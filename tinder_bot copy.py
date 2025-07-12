#!/usr/bin/env python3
"""
Enhanced Anti-Detection Tinder Automation Bot - v2.0 FIXED
Implements triple request patterns and sophisticated anti-detection measures
"""

import sqlite3
import configparser
import time
import random
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import traceback
import pytz
import signal
import hashlib
import threading
from dataclasses import dataclass
from enum import Enum

# Fix SQLite datetime handling for Python 3.12+
def adapt_datetime(dt):
    """Convert datetime to string for SQLite storage"""
    return dt.isoformat()

def convert_datetime(s):
    """Convert string back to datetime from SQLite"""
    return datetime.fromisoformat(s.decode())

# Register datetime adapters
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("timestamp", convert_datetime)

from tinder_api import TinderApi

class SessionPhase(Enum):
    """Different phases of app session for realistic behavior"""
    STARTUP = "startup"
    PROFILE_UPDATE = "profile_update"
    BROWSING = "browsing"
    LIKING = "liking"
    MAINTENANCE = "maintenance"
    COOLDOWN = "cooldown"

@dataclass
class RequestPattern:
    """Represents a request pattern with timing and repetition"""
    endpoint: str
    method: str
    repeat_count: int = 1
    delay_range: Tuple[float, float] = (0.5, 2.0)
    critical: bool = True  # If False, can skip on errors

class EnhancedTinderBot:
    """Enhanced Tinder bot with sophisticated anti-detection patterns"""
    
    def __init__(self, config_path: str = "config.ini"):
        self.config_path = config_path
        self.config = self.load_config()
        
        # Set PROCESS_NUMBER before setup_logging
        self.PROCESS_NUMBER = self.config.get('process_number', 1)
        
        self.setup_logging()
        self.setup_database()
        
        # Load data files
        self.cities = self.load_cities()
        self.usernames = self.load_usernames()
        
        # Enhanced anti-ban settings with more randomization
        self.BASE_DELAYS = {
            'micro': (0.1, 0.5),      # Between rapid requests
            'short': (0.5, 2.0),      # Normal delays
            'medium': (2.0, 5.0),     # Between operations
            'long': (5.0, 15.0),      # Between major actions
            'break': (30.0, 120.0),   # Random breaks
            'session_gap': (300, 900) # Between sessions
        }
        
        # Request patterns based on HAR analysis
        self.REQUEST_PATTERNS = {
            'startup': [
                RequestPattern('healthcheck_auth', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('buckets', 'POST', 1, self.BASE_DELAYS['short']),
                RequestPattern('device_check', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('profile_consents', 'POST', 1, self.BASE_DELAYS['medium']),
                RequestPattern('device_check', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('profile', 'GET', 1, self.BASE_DELAYS['short']),
                RequestPattern('inbox_messages', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('matches', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('fast_match_count', 'GET', 1, self.BASE_DELAYS['short']),
                RequestPattern('user_language_preferences', 'POST', 1, self.BASE_DELAYS['medium']),
                RequestPattern('updates', 'POST', 1, self.BASE_DELAYS['short']),
                RequestPattern('profile_meter', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('campaigns', 'GET', 1, self.BASE_DELAYS['short']),
                RequestPattern('push_devices', 'POST', 2, self.BASE_DELAYS['micro']),  # Often called twice
                RequestPattern('meta_post', 'POST', 1, self.BASE_DELAYS['medium']),
            ],
            'profile_check': [
                RequestPattern('fast_match_count', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('profile_feature_access', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('payment_methods', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('my_likes', 'GET', 1, self.BASE_DELAYS['short']),
                RequestPattern('duos', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('recommendations', 'GET', 3, self.BASE_DELAYS['short']),  # Triple pattern
                RequestPattern('campaigns_extended', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('subscription_features', 'GET', 2, self.BASE_DELAYS['micro']),
            ],
            'liked_me_processing': [
                RequestPattern('fast_match_count', 'GET', 3, self.BASE_DELAYS['micro']),  # Triple check
                RequestPattern('fast_match_newcount', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('liked_me_batch', 'GET', 1, self.BASE_DELAYS['short']),
                RequestPattern('fast_match_teaser', 'GET', 1, self.BASE_DELAYS['micro']),
            ],
            'maintenance': [
                RequestPattern('updates', 'POST', 1, self.BASE_DELAYS['short']),
                RequestPattern('received_messages', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('subscription_features', 'GET', 2, self.BASE_DELAYS['micro']),
                RequestPattern('profile_meter', 'GET', 1, self.BASE_DELAYS['micro']),
                RequestPattern('recommendations', 'GET', 1, self.BASE_DELAYS['short']),
            ]
        }
        
        # Session state tracking
        self.current_session = {
            'phase': SessionPhase.STARTUP,
            'start_time': None,
            'actions_count': 0,
            'last_break': None,
            'request_count': 0,
            'error_count': 0
        }
        
        # Advanced timing controls
        self.TIMING_CONFIG = {
            'max_actions_before_break': (15, 25),
            'break_duration': (45, 180),
            'session_duration': (600, 1800),  # 10-30 minutes
            'between_sessions': (900, 2700),  # 15-45 minutes
            'max_likes_per_session': self.config.get('max_likes_per_session', 25),
            'request_burst_limit': 5,  # Max rapid requests
            'burst_cooldown': (10, 30),  # Cooldown after burst
        }
        
        # Error recovery
        self.MAX_CONSECUTIVE_ERRORS = 3
        self.ERROR_COOLDOWN = 180  # 3 minutes
        self.BAN_INDICATORS = [
            'rate_limited_until',
            'APPEAL_BAN',
            'account_disabled',
            'temporarily_unavailable',
            'too_many_requests'
        ]
        
        # Request timing tracker
        self.request_history = []
        self.last_request_time = 0
        
        # Profile cache with TTL
        self.profile_cache = {}
        self.profile_cache_ttl = 300  # 5 minutes
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.running = True
        self.print_startup_info()
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print("\n🛑 Shutdown signal received, stopping gracefully...")
        self.running = False
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration with dual delay settings"""
        if not os.path.exists(self.config_path):
            print(f"❌ ERROR: Config file '{self.config_path}' not found!")
            print("Creating default config.ini...")
            self.create_default_config()
            print("✅ Default config created. Please edit it with your settings.")
            sys.exit(0)
        
        config = configparser.ConfigParser(interpolation=None)
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config.read_file(f)
        except UnicodeDecodeError:
            with open(self.config_path, 'r', encoding='latin-1') as f:
                config.read_file(f)
        
        if 'DEFAULT' not in config:
            print(f"❌ ERROR: No [DEFAULT] section found in config file!")
            sys.exit(1)
        
        default = config['DEFAULT']
        
        loaded_config = {
            # Profile settings
            'bio': default.get('Bio', ''),
            'prompt_text': default.get('PromptText', ''),
            'prompt_id': default.get('prompt_id', ''),
            
            # Core automation settings
            'like_users_who_liked_me': default.getboolean('LikeUsersWhoLikedMe', True),
            'process_accounts': default.getboolean('ProcessAccounts', True),
            'swipe_liked_me_gold_if_over': default.getint('SwipeLikedMeGoldIfOver', 50),
            'swipe_time': default.get('Swipetime', '0-23'),
            'percentage': default.getint('Percentage', 100),
            'max_likes_per_day': default.getint('MaxLikesPerDay', 80),
            'wait_between_cycles': default.getint('WaitBetweenCycles', 900),  # Changed to 15 minutes
            
            # NEW: Dual delay settings
            'delay_after_page_fetch': default.getfloat('DelayAfterPageFetch', 0.5),
            'delay_between_likes': default.getfloat('DelayBetweenLikes', 0.1),
            'get_like_count_time': default.get('GetLikeCountTime', '16-18'),

            # Session management
            'max_likes_per_session': default.getint('MaxLikesPerSession', 100000),
            'session_duration_min': default.getint('SessionDurationMin', 600),
            'session_duration_max': default.getint('SessionDurationMax', 1800),
            'between_session_min': default.getint('BetweenSessionMin', 900),
            'between_session_max': default.getint('BetweenSessionMax', 2700),
            
            # Processing settings
            'process_all_liked_me': default.getboolean('ProcessAllLikedMe', True),
            'liked_me_count_per_request': default.getint('LikedMeCountPerRequest', 20),
            'max_liked_me_total': default.getint('MaxLikedMeTotal', 999999),
            'user_traveling_in_likes': default.getboolean('UserTravelingInLikes', True),
            'pass_probability': default.getfloat('PassProbability', 0),
            
            # Profile update settings
            'use_existing_passport_location': default.getboolean('UseExistingPassportLocation', True),
            'update_bio': default.getboolean('UpdateBio', True),
            'add_prompt_to_profile': default.getboolean('AddPromptToProfile', True),
            
            # System settings
            'max_workers': default.getint('MaxWorkers', 1),
            'process_number': default.getint('ProcessNumber', 1),
            'tinders_per_username': default.getint('TindersPerUsername', 1),
            'auto_restart_on_error': default.getboolean('AutoRestartOnError', True),
            
            # Database and logging
            'database_backup_interval': default.getint('DatabaseBackupInterval', 3600),
            'error_retry_delay': default.getint('ErrorRetryDelay', 180),
            'detailed_logging': default.getboolean('DetailedLogging', False),
        }
        
        print(f"✅ Clean configuration loaded successfully")
        return loaded_config


        

    def create_default_config(self):
        """Create enhanced default config.ini file"""
        config_content = """[DEFAULT]
    # ============================================
    # PROFILE SETTINGS
    # ============================================
    Bio = Hey there! I'm %username%! Love exploring new places and meeting interesting people! 🌟
    PromptText = Ask me about my adventures with %username%
    prompt_id = pro_3

    # ============================================
    # CORE AUTOMATION SETTINGS
    # ============================================
    ProcessAccounts = True
    LikeUsersWhoLikedMe = True
    SwipeLikedMeGoldIfOver = 50
    ExpiringSoonDays = 7
    Swipetime = 8-22
    Percentage = 75
    MaxLikesPerDay = 80
    WaitBetweenCycles = 900

    # ============================================
    # DUAL DELAY SETTINGS (NEW)
    # ============================================
    DelayAfterPageFetch = 0.5
    DelayBetweenLikes = 0.1

    # ============================================
    # ENHANCED ANTI-DETECTION SETTINGS
    # ============================================
    TripleRequestPattern = True
    RealisticTimingVariance = 0.3
    RandomBreakProbability = 0.15
    SessionPhaseTransitions = True
    AdaptiveDelays = True
    BurstRequestSimulation = True

    # ============================================
    # REQUEST TIMING SETTINGS (CRITICAL FOR STEALTH)
    # ============================================
    MinRequestInterval = 0.05
    MaxRequestInterval = 0.3
    LikeDelayMin = 3.0
    LikeDelayMax = 12.0

    # ============================================
    # SESSION MANAGEMENT
    # ============================================
    MaxLikesPerSession = 25
    SessionDurationMin = 600
    SessionDurationMax = 1800
    BetweenSessionMin = 900
    BetweenSessionMax = 2700

    # ============================================
    # COMPLETE CYCLE PROCESSING
    # ============================================
    ProcessAllLikedMe = True
    LikedMeCountPerRequest = 20
    MaxLikedMeTotal = 999999

    # ============================================
    # LIKE BEHAVIOR SETTINGS
    # ============================================
    UserTravelingInLikes = False
    PassProbability = 0.25
    ExplicitPassProbability = 0.3

    # ============================================
    # PROFILE UPDATE SETTINGS
    # ============================================
    UseExistingPassportLocation = True
    UpdateBio = True
    AddPromptToProfile = True
    RemoveOldPrompts = True

    # ============================================
    # PROCESSING SETTINGS
    # ============================================
    MaxWorkers = 1
    ProcessNumber = 1
    TindersPerUsername = 1

    # ============================================
    # ERROR HANDLING & RECOVERY
    # ============================================
    AutoRestartOnError = True
    ErrorRetryDelay = 180
    MaxConsecutiveErrors = 3
    BanDetectionSensitivity = 0.8

    # ============================================
    # LOGGING & DATABASE
    # ============================================
    DatabaseBackupInterval = 3600
    DetailedLogging = False
    LogRequestTimings = False
    """
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
    
    
    def setup_logging(self):
        """Setup enhanced logging configuration with UTF-8 support"""
        os.makedirs('logs', exist_ok=True)
        
        log_filename = f'logs/enhanced_tinder_bot_p{self.PROCESS_NUMBER}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        # Set log level based on config
        log_level = logging.DEBUG if self.config.get('detailed_logging', False) else logging.INFO
        
        # Create file handler with UTF-8 encoding
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(log_level)
        
        # Create console handler with UTF-8 encoding (for emojis)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # Set encoding for console on Windows to handle emojis
        if hasattr(console_handler.stream, 'reconfigure'):
            try:
                console_handler.stream.reconfigure(encoding='utf-8')
            except:
                pass
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - P%(process)d - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            handlers=[file_handler, console_handler],
            force=True  # Override any existing configuration
        )
        
        # Reduce noise from requests library
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        logging.info("Enhanced Anti-Detection TinderBot logging initialized")
    
    def setup_database(self):
        """Initialize enhanced database with better tracking"""
        print("📊 Setting up enhanced database...")
        
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                
                # Enhanced accounts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        auth_token TEXT NOT NULL,
                        refresh_token TEXT NOT NULL,
                        device_id TEXT NOT NULL,
                        persistent_device_id TEXT NOT NULL,
                        install_id TEXT NOT NULL,
                        appsflyer_id TEXT,
                        advertising_id TEXT,
                        device_ram TEXT DEFAULT '5',
                        os_version TEXT DEFAULT '34',
                        proxy TEXT,
                        user_id TEXT,
                        assigned_city TEXT,
                        assigned_username TEXT,
                        coordinates_lat REAL,
                        coordinates_lon REAL,
                        timezone_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'active',
                        error_count INTEGER DEFAULT 0,
                        last_error TEXT,
                        last_error_time TIMESTAMP,
                        ban_score REAL DEFAULT 0.0,
                        last_ban_check TIMESTAMP,
                        session_count INTEGER DEFAULT 0,
                        total_requests INTEGER DEFAULT 0,
                        total_likes INTEGER DEFAULT 0,
                        UNIQUE(device_id)
                    )
                """)
                # Add this to the setup_database method in the account_status table creation:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS account_status (
                        account_id INTEGER PRIMARY KEY,
                        is_gold BOOLEAN DEFAULT FALSE,
                        gold_expires_at TIMESTAMP,
                        liked_me_count INTEGER DEFAULT 0,
                        last_liked_me_check TIMESTAMP,  -- ADD THIS LINE
                        last_liked_me_check_count INTEGER DEFAULT 0,  -- ADD THIS LINE
                        was_over_threshold BOOLEAN DEFAULT FALSE,
                        liked_me_processed BOOLEAN DEFAULT FALSE,
                        bio_updated BOOLEAN DEFAULT FALSE,
                        prompts_updated BOOLEAN DEFAULT FALSE,
                        current_passport_lat REAL,
                        current_passport_lon REAL,
                        current_passport_location TEXT,
                        last_session_start TIMESTAMP,
                        last_session_end TIMESTAMP,
                        session_likes_count INTEGER DEFAULT 0,
                        total_session_actions INTEGER DEFAULT 0,
                        last_action_time TIMESTAMP,
                        last_break_time TIMESTAMP,
                        consecutive_errors INTEGER DEFAULT 0,
                        last_activity_date TEXT,
                        current_session_phase TEXT DEFAULT 'startup',
                        request_burst_count INTEGER DEFAULT 0,
                        last_burst_time TIMESTAMP,
                        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                    )
                """)
                # Enhanced session tracking
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS enhanced_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER,
                        session_start TIMESTAMP,
                        session_end TIMESTAMP,
                        session_phase TEXT,
                        duration_seconds INTEGER,
                        requests_made INTEGER DEFAULT 0,
                        likes_sent INTEGER DEFAULT 0,
                        passes_sent INTEGER DEFAULT 0,
                        matches_gained INTEGER DEFAULT 0,
                        errors_encountered INTEGER DEFAULT 0,
                        break_count INTEGER DEFAULT 0,
                        avg_request_interval REAL,
                        session_quality_score REAL,
                        detected_issues TEXT,
                        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                    )
                """)
                
                # Request timing analysis
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS request_timing (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER,
                        session_id INTEGER,
                        request_type TEXT,
                        request_time TIMESTAMP,
                        response_time_ms INTEGER,
                        status_code INTEGER,
                        interval_from_previous REAL,
                        is_triple_pattern BOOLEAN DEFAULT FALSE,
                        pattern_position INTEGER,
                        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                        FOREIGN KEY (session_id) REFERENCES enhanced_sessions(id) ON DELETE CASCADE
                    )
                """)
                
                # Ban detection tracking
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ban_indicators (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER,
                        indicator_type TEXT,
                        indicator_value TEXT,
                        severity REAL,
                        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMP,
                        notes TEXT,
                        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                    )
                """)
                
                # Enhanced activity tracking
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS enhanced_activity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER,
                        session_id INTEGER,
                        activity_type TEXT,
                        target_user_id TEXT,
                        success BOOLEAN,
                        timing_ms INTEGER,
                        request_pattern TEXT,
                        phase TEXT,
                        details JSON,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                        FOREIGN KEY (session_id) REFERENCES enhanced_sessions(id) ON DELETE CASCADE
                    )
                """)
                
                # Username tracking table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS username_city_tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        city TEXT NOT NULL,
                        account_id INTEGER,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (account_id) REFERENCES accounts(id)
                    )
                """)
                
                # Username usage table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS username_usage (
                        username TEXT,
                        city TEXT,
                        used_count INTEGER DEFAULT 0,
                        last_used TIMESTAMP,
                        PRIMARY KEY (username, city)
                    )
                """)
                
                # Dead accounts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dead_accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        auth_token TEXT,
                        refresh_token TEXT,
                        device_id TEXT,
                        persistent_device_id TEXT,
                        reason TEXT,
                        error_details TEXT,
                        marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Keep existing tables with modifications
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS account_status (
                        account_id INTEGER PRIMARY KEY,
                        is_gold BOOLEAN DEFAULT FALSE,
                        gold_expires_at TIMESTAMP,
                        liked_me_count INTEGER DEFAULT 0,
                        was_over_threshold BOOLEAN DEFAULT FALSE,
                        liked_me_processed BOOLEAN DEFAULT FALSE,
                        bio_updated BOOLEAN DEFAULT FALSE,
                        prompts_updated BOOLEAN DEFAULT FALSE,
                        current_passport_lat REAL,
                        current_passport_lon REAL,
                        current_passport_location TEXT,
                        last_session_start TIMESTAMP,
                        last_session_end TIMESTAMP,
                        session_likes_count INTEGER DEFAULT 0,
                        total_session_actions INTEGER DEFAULT 0,
                        last_action_time TIMESTAMP,
                        last_break_time TIMESTAMP,
                        consecutive_errors INTEGER DEFAULT 0,
                        last_activity_date TEXT,
                        current_session_phase TEXT DEFAULT 'startup',
                        request_burst_count INTEGER DEFAULT 0,
                        last_burst_time TIMESTAMP,
                        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_status_ban ON accounts(status, ban_score)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_enhanced_sessions_account_time ON enhanced_sessions(account_id, session_start)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_request_timing_account_session ON request_timing(account_id, session_id, request_time)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ban_indicators_account_severity ON ban_indicators(account_id, severity, detected_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_enhanced_activity_account_time ON enhanced_activity(account_id, timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_username_city_tracking ON username_city_tracking(username, city)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_username_usage ON username_usage(username, city)")
                
                conn.commit()
                
            print("✅ Enhanced database setup complete")
            
        except Exception as e:
            print(f"❌ Enhanced database setup error: {e}")
            logging.error(f"Enhanced database setup error: {e}")
            raise
   
   
    def should_process_accounts_now(self) -> bool:
        """Check if we should process accounts based on swipe time"""
        if not self.config['process_accounts']:
            return False
        
        # Get current hour
        current_hour = datetime.now().hour
        start_hour, end_hour = map(int, self.config['swipe_time'].split('-'))
        
        # Check if in swipe time
        if start_hour <= end_hour:
            in_swipe_time = start_hour <= current_hour <= end_hour
        else:
            in_swipe_time = current_hour >= start_hour or current_hour <= end_hour
        
        if not in_swipe_time:
            print(f"⏰ Outside swipe time ({self.config['swipe_time']}). Current hour: {current_hour}")
            return False
        
        return True
   
   
   
    def print_startup_info(self):
        """Print enhanced startup information"""
        print("=" * 70)
        print("🔥 ENHANCED ANTI-DETECTION TINDER BOT v2.0 🔥")
        print("🎯 DUAL DELAY SYSTEM & FAST PROCESSING 🎯")
        print("=" * 70)
        
        # Get database stats
        total_likes_alltime, likes_today = self.get_database_stats()
        
        print(f"📂 Config file: {self.config_path}")
        print(f"🏙️  Cities loaded: {len(self.cities)}")
        print(f"👤 Usernames loaded: {len(self.usernames)}")
        print(f"⚙️  Processing enabled: {self.config['process_accounts']}")
        print(f"💕 Like users who liked me: {self.config['like_users_who_liked_me']}")
        print(f"🕐 Swipe time: {self.config['swipe_time']}")
        print(f"📊 Like percentage: {self.config['percentage']}%")
        print(f"🚫 Max likes per day: {self.config['max_likes_per_day']}")
        print(f"🔄 Max likes per session: {self.config['max_likes_per_session']}")
        
        # NEW: Show dual delay settings
        print(f"⏱️  Page fetch delay: {self.config['delay_after_page_fetch']}s")
        print(f"⏱️  Between likes delay: {self.config['delay_between_likes']}s")
        
        print(f"🎯 User traveling in likes: {self.config['user_traveling_in_likes']}")
        print(f"🔄 Process all liked me: {self.config['process_all_liked_me']}")
        print(f"📦 Users per request: {self.config['liked_me_count_per_request']}")
        print("=" * 70)
        print("📊 DATABASE STATISTICS:")
        print(f"💕 Total likes all-time: {total_likes_alltime}")
        print(f"📅 Likes sent today: {likes_today}")
        print("=" * 70)
        
        logging.info("Enhanced Anti-Detection TinderBot v2.0 initialized")
    def get_database_stats(self) -> Tuple[int, int]:
        """Get enhanced database statistics"""
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                
                # Total likes all-time
                cursor.execute("SELECT COUNT(*) FROM enhanced_activity WHERE activity_type = 'like' AND success = 1")
                total_likes = cursor.fetchone()[0]
                
                # Likes today
                cursor.execute("""
                    SELECT COUNT(*) FROM enhanced_activity 
                    WHERE activity_type = 'like' AND success = 1 
                    AND date(timestamp) = date('now')
                """)
                likes_today = cursor.fetchone()[0]
                
                return total_likes, likes_today
        except:
            return 0, 0
    
    def adaptive_delay(self, delay_type: str, context: str = "", factor: float = 1.0):
        """Enhanced adaptive delay system with context awareness"""
        if delay_type not in self.BASE_DELAYS:
            delay_type = 'short'
        
        base_min, base_max = self.BASE_DELAYS[delay_type]
        
        # Apply timing variance from config
        variance = self.config.get('realistic_timing_variance', 0.3)
        min_delay = base_min * factor * (1 - variance + random.random() * variance * 2)
        max_delay = base_max * factor * (1 - variance + random.random() * variance * 2)
        
        # Ensure minimum values
        min_delay = max(0.05, min_delay)
        max_delay = max(min_delay + 0.1, max_delay)
        
        # Adaptive adjustments based on session state
        if self.current_session['error_count'] > 0:
            factor *= (1 + self.current_session['error_count'] * 0.2)
        
        if self.current_session['actions_count'] > 50:
            factor *= 1.3  # Slow down as session progresses
        
        # Calculate final delay
        delay = random.uniform(min_delay, max_delay)
        
        if context and self.config.get('detailed_logging', False):
            logging.debug(f"Adaptive delay for {context}: {delay:.2f}s (type: {delay_type}, factor: {factor:.2f})")
        
        time.sleep(delay)
        return delay
    
    def execute_request_pattern(self, api: TinderApi, pattern_name: str, account_id: int, session_id: int) -> Dict[str, Any]:
        """Execute a request pattern with triple patterns and timing analysis"""
        if pattern_name not in self.REQUEST_PATTERNS:
            logging.warning(f"Unknown request pattern: {pattern_name}")
            return {'success': False, 'error': 'Unknown pattern'}
        
        patterns = self.REQUEST_PATTERNS[pattern_name]
        results = {'success': True, 'requests_made': 0, 'errors': 0, 'timings': []}
        
        for pattern in patterns:
            if not self.running:
                break
            
            try:
                # Execute the request(s) based on repeat count
                for repeat in range(pattern.repeat_count):
                    if not self.running:
                        break
                    
                    start_time = time.time()
                    
                    # Execute the actual request
                    request_success = self._execute_single_request(api, pattern.endpoint, pattern.method)
                    
                    end_time = time.time()
                    response_time_ms = int((end_time - start_time) * 1000)
                    
                    # Track timing
                    if self.config.get('log_request_timings', False):
                        self._log_request_timing(
                            account_id, session_id, pattern.endpoint, 
                            response_time_ms, request_success, 
                            pattern.repeat_count > 1, repeat + 1
                        )
                    
                    results['requests_made'] += 1
                    results['timings'].append(response_time_ms)
                    
                    if not request_success:
                        results['errors'] += 1
                        if pattern.critical:
                            logging.warning(f"Critical request failed: {pattern.endpoint}")
                            # Don't break immediately, but log the issue
                        else:
                            logging.debug(f"Non-critical request failed: {pattern.endpoint}")
                    
                    # Delay between repeats (for triple patterns)
                    if repeat < pattern.repeat_count - 1:
                        self.adaptive_delay('micro', f"{pattern.endpoint} repeat {repeat + 1}")
                
                # Delay before next pattern
                if pattern != patterns[-1]:  # Not the last pattern
                    self.adaptive_delay('short' if pattern.critical else 'micro', f"after {pattern.endpoint}")
                
            except Exception as e:
                logging.error(f"Error executing pattern {pattern.endpoint}: {e}")
                results['errors'] += 1
                results['success'] = False
        
        # Update session state
        self.current_session['request_count'] += results['requests_made']
        self.current_session['error_count'] += results['errors']
        
        return results
    
    def _get_total_matches(self, account_id: int) -> int:
        """Get total matches for account"""
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT SUM(matches_gained) FROM enhanced_sessions 
                    WHERE account_id = ?
                """, (account_id,))
                result = cursor.fetchone()
                return result[0] if result and result[0] else 0
        except:
            return 0
    
    

    def _execute_single_request(self, api: TinderApi, endpoint: str, method: str) -> bool:
        """Execute a single API request with enhanced error handling and proper 403/401 detection"""
        try:
            # Map endpoint names to actual API methods
            endpoint_map = {
                'healthcheck_auth': lambda: api.healthcheck_auth(),
                'buckets': lambda: api.buckets(),
                'device_check': lambda: api.device_check(False),
                'profile_consents': lambda: api.send_profile_consents(),
                'profile': lambda: api.profile(),
                'inbox_messages': lambda: api.get_inbox_messages(),
                'matches': lambda: api.get_matches(100),
                'fast_match_count': lambda: api.liked_me_count(),
                'user_language_preferences': lambda: api.update_user_language_preferences(),
                'updates': lambda: api.get_updates(),
                'profile_meter': lambda: api.profileMeter(),
                'campaigns': lambda: api.get_campaigns(['live_ops', 'mini_merch', 'modal']),
                'push_devices': lambda: api.register_push_device(self._generate_device_token()),
                'meta_post': lambda: api.meta_post(api.latitude, api.longitude),
                'profile_feature_access': lambda: api.profile(include_params="feature_access"),
                'payment_methods': lambda: api.get_payment_methods(),
                'my_likes': lambda: api.myLikes(),
                'duos': lambda: api.get_duos(),
                'recommendations': lambda: api.get_recommendations(),
                'campaigns_extended': lambda: api.get_campaigns(['banner', 'live_ops', 'mini_merch', 'modal', 'rec_card']),
                'subscription_features': lambda: api.get_subscription_features(),
                'fast_match_newcount': lambda: api.get_fast_match_newcount(self._generate_count_token()),
                'liked_me_batch': lambda: api.liked_me(100),
                'fast_match_teaser': lambda: api.get_fast_match_teaser(),
                'received_messages': lambda: api.get_received_messages(),
            }
            
            if endpoint not in endpoint_map:
                logging.warning(f"Unknown endpoint: {endpoint}")
                return False
            
            # Execute the request
            result = endpoint_map[endpoint]()
            
            # Check for 403/401 errors by looking at the API's last response
            if hasattr(api, '_last_response_status'):
                status_code = api._last_response_status
                
                if status_code == 403:
                    # Account is banned - get account info and mark as banned
                    account_info = getattr(self, '_current_account', {})
                    account_id = account_info.get('id')
                    city = account_info.get('assigned_city', 'Unknown')
                    
                    if account_id:
                        logging.warning(f"Account {account_id} ({city}) received 403 - marking as banned")
                        self._mark_account_banned(account_id)
                    else:
                        logging.warning(f"Account ({city}) received 403 - marking as banned")
                    
                    # Print final message
                    matches = self._get_total_matches(account_id) if account_id else 0
                    print(f"Account - {city} finished with {matches} matches (BANNED)")
                    return False
                    
                elif status_code == 401:
                    # Token expired - mark as dead
                    account_info = getattr(self, '_current_account', {})
                    account_id = account_info.get('id')
                    city = account_info.get('assigned_city', 'Unknown')
                    
                    if account_id:
                        logging.warning(f"Account {account_id} ({city}) received 401 - token expired")
                        self._mark_account_dead_from_id(account_id, "Token expired", "401 unauthorized")
                    
                    matches = self._get_total_matches(account_id) if account_id else 0
                    print(f"Account - {city} finished with {matches} matches (TOKEN EXPIRED)")
                    return False
            
            # Check for ban indicators in successful responses
            if result and isinstance(result, dict):
                ban_score = self._check_ban_indicators(result)
                if ban_score >= 0.8:
                    account_info = getattr(self, '_current_account', {})
                    account_id = account_info.get('id')
                    if account_id:
                        self._mark_account_banned(account_id)
                    return False
            
            return result is not None
            
        except Exception as e:
            logging.error(f"Request execution error for {endpoint}: {e}")
            return False
    
    
    
    def _generate_device_token(self) -> str:
        """Generate realistic device token for push notifications"""
        # Generate a token that looks like a real FCM token
        prefix = "d7EjmRKARdWgykP-B9mfsI:APA91bFABX7qlQRJVBR8XCAd0OlxTHiESzqKjNwS_sCUoGu-QK_NpP-iyjyyCFOGzd9j89lIbP54pCGgkKoWrD38FioFOAKXCLpXLzsEpBBp4J6zC4tGKmQ"
        return prefix
    
    def _generate_count_token(self) -> str:
        """Generate count token for fast match requests"""
        import base64
        timestamp_ms = int(time.time() * 1000)
        token_data = json.dumps({"timestamp": timestamp_ms})
        return base64.b64encode(token_data.encode()).decode()
    
    def _log_request_timing(self, account_id: int, session_id: int, request_type: str, 
                           response_time_ms: int, success: bool, is_triple: bool, position: int):
        """Log request timing for analysis"""
        try:
            current_time = time.time()
            interval_from_previous = current_time - self.last_request_time if self.last_request_time > 0 else 0
            self.last_request_time = current_time
            
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO request_timing 
                    (account_id, session_id, request_type, request_time, response_time_ms, 
                     status_code, interval_from_previous, is_triple_pattern, pattern_position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account_id, session_id, request_type, datetime.now(), response_time_ms,
                    200 if success else 400, interval_from_previous, is_triple, position
                ))
                conn.commit()
        except Exception as e:
            logging.error(f"Error logging request timing: {e}")
    
    def _check_ban_indicators(self, response: Dict) -> float:
        """Enhanced ban detection with scoring system"""
        ban_score = 0.0
        indicators = []
        
        response_str = str(response).lower()
        
        # Check for explicit ban indicators
        for indicator in self.BAN_INDICATORS:
            if indicator.lower() in response_str:
                severity = 1.0 if indicator in ['APPEAL_BAN', 'account_disabled'] else 0.7
                ban_score += severity
                indicators.append((indicator, severity))
        
        # Check for rate limiting patterns
        if 'rate_limited_until' in response_str or 'too_many_requests' in response_str:
            ban_score += 0.5
            indicators.append(('rate_limiting', 0.5))
        
        # Check for empty responses that shouldn't be empty
        if isinstance(response, dict) and not response:
            ban_score += 0.2
            indicators.append(('empty_response', 0.2))
        
        # Log indicators if found
        if indicators and ban_score >= self.config.get('ban_detection_sensitivity', 0.8):
            logging.warning(f"Ban indicators detected (score: {ban_score:.2f}): {indicators}")
        
        return ban_score
    
    
    def transition_session_phase(self, new_phase: SessionPhase, account_id: int):
        """Manage session phase transitions with appropriate delays"""
        old_phase = self.current_session['phase']
        
        if old_phase == new_phase:
            return
        
        self.current_session['phase'] = new_phase
        
        # Update database
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE account_status 
                    SET current_session_phase = ?
                    WHERE account_id = ?
                """, (new_phase.value, account_id))
                conn.commit()
        except Exception as e:
            logging.error(f"Error updating session phase: {e}")
        
        # Phase transition delays
        transition_delays = {
            (SessionPhase.STARTUP, SessionPhase.PROFILE_UPDATE): 'medium',
            (SessionPhase.PROFILE_UPDATE, SessionPhase.BROWSING): 'long',
            (SessionPhase.BROWSING, SessionPhase.LIKING): 'medium',
            (SessionPhase.LIKING, SessionPhase.MAINTENANCE): 'short',
            (SessionPhase.MAINTENANCE, SessionPhase.LIKING): 'medium',
            (SessionPhase.LIKING, SessionPhase.COOLDOWN): 'long',
        }
        
        delay_type = transition_delays.get((old_phase, new_phase), 'short')
        self.adaptive_delay(delay_type, f"phase transition {old_phase.value} -> {new_phase.value}")
    
    
    def should_take_random_break(self) -> bool:
        """Determine if should take a random break based on various factors"""
        pass
    
    def take_random_break(self, account_id: int, reason: str = "random"):
        """Take a random break with realistic activity"""
        pass 
    
    def load_cities(self) -> List[Dict[str, Any]]:
        """Load cities with enhanced validation"""
        cities = []
        if not os.path.exists('cities.txt'):
            print("⚠️  WARNING: cities.txt not found - location features disabled")
            return cities
        
        try:
            with open('cities.txt', 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(',')
                        if len(parts) >= 4:
                            try:
                                lat = float(parts[2].strip())
                                lon = float(parts[3].strip())
                                
                                # Validate coordinates
                                if -90 <= lat <= 90 and -180 <= lon <= 180:
                                    cities.append({
                                        'city': parts[0].strip(),
                                        'country': parts[1].strip(),
                                        'lat': lat,
                                        'lon': lon
                                    })
                                else:
                                    print(f"⚠️  Invalid coordinates on line {line_num}: {line}")
                            except ValueError:
                                print(f"⚠️  Invalid number format on line {line_num}: {line}")
                        else:
                            print(f"⚠️  Invalid format on line {line_num}: {line}")
        except Exception as e:
            print(f"❌ Error loading cities: {e}")
        
        print(f"✅ Loaded {len(cities)} valid cities")
        return cities
    
    def load_usernames(self) -> List[str]:
        """Load usernames with no defaults - error if none found"""
        usernames = []
        
        if not os.path.exists('usernames.txt'):
            print("❌ ERROR: usernames.txt not found!")
            print("Please create usernames.txt with one username per line")
            return []
        
        try:
            # Try different encodings to handle various file formats
            content = None
            encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            
            for encoding in encodings_to_try:
                try:
                    with open('usernames.txt', 'r', encoding=encoding) as f:
                        content = f.readlines()
                    print(f"✅ Successfully read usernames.txt with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"❌ Error reading with {encoding}: {e}")
                    continue
            
            if not content:
                print("❌ Could not read usernames.txt with any encoding")
                return []
            
            invalid_usernames = []
            
            for line_num, line in enumerate(content, 1):
                # Clean the line
                line = line.strip()
                
                # Remove BOM and other problematic characters
                line = line.replace('\ufeff', '').replace('\x00', '')
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Enhanced username validation
                if self._is_valid_username(line):
                    usernames.append(line)
                else:
                    invalid_usernames.append((line_num, line))
            
            # Report validation results
            if invalid_usernames:
                print(f"⚠️  Found {len(invalid_usernames)} invalid usernames:")
                for line_num, invalid_name in invalid_usernames[:5]:  # Show first 5
                    print(f"      Line {line_num}: '{invalid_name}'")
                if len(invalid_usernames) > 5:
                    print(f"      ... and {len(invalid_usernames) - 5} more")
            
            if not usernames:
                print("❌ ERROR: No valid usernames found in usernames.txt!")
                print("Please add usernames to usernames.txt (one per line)")
                return []
            
            print(f"✅ Successfully loaded {len(usernames)} usernames")
            return usernames
            
        except Exception as e:
            print(f"❌ Error loading usernames: {e}")
            return []


    def _is_valid_username(self, username: str) -> bool:
        """Enhanced username validation with more flexible rules"""
        if username:
            return True
        
        
        # Character validation - allow letters, numbers, spaces, hyphens, underscores, apostrophes
        # This covers names like "Mary-Jane", "O'Connor", "Van Der Berg", etc.
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_\'.')
        if not all(c in allowed_chars for c in username):
            return False
        
        # Must contain at least one letter
        if not any(c.isalpha() for c in username):
            return False
        
        # Cannot start or end with special characters
        if username[0] in ' -_\'.':
            return False
        if username[-1] in ' -_\'.':
            return False
        
        # Cannot have consecutive special characters
        special_chars = ' -_\'.'
        for i in range(len(username) - 1):
            if username[i] in special_chars and username[i + 1] in special_chars:
                return False
        
        return True

    def debug_username_loading(self):
        """Debug method to check username loading issues"""
        print("\n🔍 DEBUG: Username Loading Analysis")
        print("=" * 50)
        
        # Check if file exists
        if not os.path.exists('usernames.txt'):
            print("❌ usernames.txt file does not exist")
            return
        
        print("✅ usernames.txt file exists")
        
        # Check file size
        try:
            file_size = os.path.getsize('usernames.txt')
            print(f"📁 File size: {file_size} bytes")
            
            if file_size == 0:
                print("❌ File is empty")
                return
        except Exception as e:
            print(f"❌ Error checking file size: {e}")
            return
        
        # Try to read raw content
        try:
            with open('usernames.txt', 'rb') as f:
                raw_content = f.read()
            print(f"📝 Raw content preview (first 200 bytes):")
            print(repr(raw_content[:200]))
        except Exception as e:
            print(f"❌ Error reading raw content: {e}")
            return
        
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                with open('usernames.txt', 'r', encoding=encoding) as f:
                    lines = f.readlines()
                print(f"✅ Successfully read with {encoding}: {len(lines)} lines")
                
                # Show first few lines
                print(f"   First 5 lines with {encoding}:")
                for i, line in enumerate(lines[:5], 1):
                    print(f"      Line {i}: {repr(line)}")
                break
            except Exception as e:
                print(f"❌ Failed with {encoding}: {e}")
        
        # Test the validation function
        print("\n🧪 Testing username validation:")
        test_names = ['Alex', 'Jordan123', 'Mary-Jane', "O'Connor", 'a', 'verylongusernamethatistoolong']
        for name in test_names:
            is_valid = self._is_valid_username(name)
            print(f"   '{name}': {'✅ Valid' if is_valid else '❌ Invalid'}")
        
        print("=" * 50)
    def log_enhanced_activity(self, account_id: int, session_id: Optional[int], activity_type: str, 
                            target_user_id: Optional[str], success: bool, timing_ms: int,
                            request_pattern: str, phase: str, details: Dict):
        """Enhanced activity logging with detailed context"""
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO enhanced_activity 
                    (account_id, session_id, activity_type, target_user_id, success, 
                     timing_ms, request_pattern, phase, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account_id, session_id, activity_type, target_user_id, success,
                    timing_ms, request_pattern, phase, json.dumps(details)
                ))
                conn.commit()
        except Exception as e:
            logging.error(f"Error logging enhanced activity: {e}")
    
    def get_ready_accounts(self) -> List[Dict]:
        """Get accounts ready for processing - exclude banned accounts"""
        if not self.config['process_accounts']:
            return []
        
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT a.*, s.* FROM accounts a
                    LEFT JOIN account_status s ON a.id = s.account_id
                    WHERE a.status = 'active' 
                    AND a.error_count < ?
                    ORDER BY s.last_session_end ASC NULLS FIRST, a.session_count ASC
                """, (self.MAX_CONSECUTIVE_ERRORS,))
                
                all_accounts = []
                ready_accounts = []
                
                for row in cursor.fetchall():
                    account = dict(zip([col[0] for col in cursor.description], row))
                    all_accounts.append(account)
                    
                    # Enhanced readiness checks
                    if not self._is_account_ready(account):
                        continue
                    
                    ready_accounts.append(account)
                
                if not ready_accounts and all_accounts:
                    print("\n📊 Account Status Summary:")
                    self._print_detailed_account_status(all_accounts)
                    
            return ready_accounts
                
        except Exception as e:
            logging.error(f"Error getting ready accounts: {e}")
            return []
    

    def _is_account_ready(self, account: Dict) -> bool:
        """Enhanced account readiness check - accounts with likes always ready"""
        account_id = account['id']
        
        # Check daily like limits
        if self.check_daily_like_limit(account_id):
            logging.debug(f"Account {account_id} hit daily like limit")
            return False
        
        # NEW: If account has likes, it's ALWAYS ready (no cooldown, no time checks)
        liked_me_count = account.get('liked_me_count', 0)
        if liked_me_count > 0:
            logging.info(f"Account {account_id} has {liked_me_count} likes - bypassing all checks")
            return True
        
        # For accounts with no likes, check timezone and swipe time
        if not self.is_in_swipe_time(account):
            logging.debug(f"Account {account_id} outside swipe time")
            return False
        
        # Check session cooldown only for accounts with no likes
        if self.needs_session_cooldown(account):
            logging.debug(f"Account {account_id} in session cooldown")
            return False
        
        # Check error rate
        total_sessions = account.get('session_count', 0)
        if total_sessions > 5:
            error_rate = account.get('error_count', 0) / total_sessions
            if error_rate > 0.3:
                logging.debug(f"Account {account_id} has high error rate: {error_rate:.2f}")
                return False
        
        # Check if it's time to check for new likes
        if self.should_check_likes_for_account(account):
            return True
        
        return False


    def _print_detailed_account_status_with_timezone(self, all_accounts: List[Dict]):
        """Print detailed status with timezone info"""
        print(f"Total accounts in database: {len(all_accounts)}")
        
        time_range = self.config.get('swipe_time', '0-23')  # Changed from get_like_count_time

        
        not_ready_reasons = {
            'daily_limit': [],
            'not_swipe_time': [],
            'cooldown': [],
            'high_error_rate': [],
            'no_likes_wrong_time': [],
            'already_checked_today': []
        }
        
        for account in all_accounts:
            account_id = account['id']
            city = account.get('assigned_city', 'Unknown')
            timezone_name = account.get('timezone_name', 'UTC')
            liked_me_count = account.get('liked_me_count', 0)
            last_check = account.get('last_liked_me_check')
            
            # Get local time
            try:
                tz = pytz.timezone(timezone_name)
                local_time = datetime.now(tz)
                local_time_str = local_time.strftime('%H:%M')
            except:
                local_time_str = 'Unknown'
                tz = pytz.UTC
                local_time = datetime.now(tz)
            
            # Check why not ready
            if self.check_daily_like_limit(account_id):
                not_ready_reasons['daily_limit'].append(f"{city}: Hit daily like limit")
            elif not self.is_in_swipe_time(account):
                not_ready_reasons['not_swipe_time'].append(f"{city}: Outside swipe time window")
            elif self.needs_session_cooldown(account):
                last_session = account.get('last_session_end')
                if last_session:
                    not_ready_reasons['cooldown'].append(f"{city}: In cooldown (last session: {last_session})")
                else:
                    not_ready_reasons['cooldown'].append(f"{city}: In cooldown")
            elif liked_me_count == 0:
                # Check if already checked today
                if last_check:
                    if isinstance(last_check, str):
                        last_check_dt = datetime.fromisoformat(last_check)
                    else:
                        last_check_dt = last_check
                    
                    if last_check_dt.tzinfo is None:
                        last_check_dt = pytz.UTC.localize(last_check_dt)
                    
                    last_check_local = last_check_dt.astimezone(tz)
                    
                    if last_check_local.date() == local_time.date():
                        not_ready_reasons['already_checked_today'].append(
                            f"{city}: Already checked at {last_check_local.strftime('%H:%M')} - no likes found"
                        )
                    else:
                        not_ready_reasons['no_likes_wrong_time'].append(
                            f"{city}: No likes, waiting for {time_range} window (currently {local_time_str})"
                        )
                else:
                    not_ready_reasons['no_likes_wrong_time'].append(
                        f"{city}: No likes, waiting for {time_range} window (currently {local_time_str})"
                    )
            else:
                # Check for high error rate
                total_sessions = account.get('session_count', 0)
                if total_sessions > 5:
                    error_rate = account.get('error_count', 0) / total_sessions
                    if error_rate > 0.3:
                        not_ready_reasons['high_error_rate'].append(
                            f"{city}: High error rate ({error_rate:.1%})"
                        )
        
        # Print categorized reasons
        for reason, accounts in not_ready_reasons.items():
            if accounts:
                reason_text = reason.replace('_', ' ').title()
                print(f"\n{reason_text} ({len(accounts)}):")
                for account_msg in accounts[:5]:  # Show first 5
                    print(f"   • {account_msg}")
                if len(accounts) > 5:
                    print(f"   ... and {len(accounts) - 5} more")


    def check_daily_like_limit(self, account_id: int) -> bool:
        """Check if account hit daily like limit"""
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM enhanced_activity 
                    WHERE account_id = ? AND activity_type = 'like' AND success = 1
                    AND date(timestamp) = date('now')
                """, (account_id,))
                
                daily_likes = cursor.fetchone()[0]
                return daily_likes >= self.config['max_likes_per_day']
        except Exception as e:
            logging.error(f"Error checking daily like limit: {e}")
            return False
    
    def is_in_swipe_time(self, account: Dict) -> bool:
        """Check if current time is within swipe hours"""
        timezone_name = account.get('timezone_name', 'UTC')
        
        try:
            tz = pytz.timezone(timezone_name)
            local_time = datetime.now(tz)
            current_hour = local_time.hour
            
            start_hour, end_hour = map(int, self.config['swipe_time'].split('-'))
            
            if start_hour <= end_hour:
                return start_hour <= current_hour <= end_hour
            else:
                return current_hour >= start_hour or current_hour <= end_hour
                
        except Exception as e:
            logging.warning(f"Error checking swipe time: {e}")
            return True
    
    def needs_session_cooldown(self, account: Dict) -> bool:
        """Check if account needs session cooldown"""
        last_session_end = account.get('last_session_end')
        if not last_session_end:
            return False
        
        try:
            if isinstance(last_session_end, str):
                last_session_end = datetime.fromisoformat(last_session_end)
            
            time_since_last = (datetime.now() - last_session_end).total_seconds()
            min_wait = self.config.get('between_session_min', 900)
            
            return time_since_last < min_wait
            
        except Exception as e:
            logging.error(f"Error checking session cooldown: {e}")
            return False
    
    def start_enhanced_session(self, account_id: int) -> int:
        """Start an enhanced session with full tracking"""
        try:
            session_start = datetime.now()
            
            # Reset session state
            self.current_session = {
                'phase': SessionPhase.STARTUP,
                'start_time': session_start,
                'actions_count': 0,
                'last_break': None,
                'request_count': 0,
                'error_count': 0
            }
            
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                
                # Create session record
                cursor.execute("""
                    INSERT INTO enhanced_sessions 
                    (account_id, session_start, session_phase)
                    VALUES (?, ?, ?)
                """, (account_id, session_start, SessionPhase.STARTUP.value))
                
                session_id = cursor.lastrowid
                
                # Update account status
                cursor.execute("""
                    UPDATE account_status 
                    SET last_session_start = ?, current_session_phase = ?,
                        session_likes_count = 0, total_session_actions = 0,
                        request_burst_count = 0
                    WHERE account_id = ?
                """, (session_start, SessionPhase.STARTUP.value, account_id))
                
                # Update account session counter
                cursor.execute("""
                    UPDATE accounts 
                    SET session_count = session_count + 1
                    WHERE id = ?
                """, (account_id,))
                
                conn.commit()
                return session_id
                
        except Exception as e:
            logging.error(f"Error starting enhanced session: {e}")
            return 0
    
    def end_enhanced_session(self, account_id: int, session_id: int, stats: Dict):
        """End enhanced session with comprehensive tracking"""
        try:
            session_end = datetime.now()
            duration = int((session_end - self.current_session['start_time']).total_seconds())
            
            # Calculate session quality score
            quality_score = self._calculate_session_quality(stats)
            
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                
                # Update session record
                cursor.execute("""
                    UPDATE enhanced_sessions 
                    SET session_end = ?, duration_seconds = ?, requests_made = ?,
                        likes_sent = ?, passes_sent = ?, matches_gained = ?,
                        errors_encountered = ?, session_quality_score = ?
                    WHERE id = ?
                """, (
                    session_end, duration, self.current_session['request_count'],
                    stats.get('likes_sent', 0), stats.get('passes_sent', 0),
                    stats.get('matches_gained', 0), self.current_session['error_count'],
                    quality_score, session_id
                ))
                
                # Update account status
                cursor.execute("""
                    UPDATE account_status 
                    SET last_session_end = ?, current_session_phase = 'cooldown'
                    WHERE account_id = ?
                """, (session_end, account_id))
                
                # Update account totals
                cursor.execute("""
                    UPDATE accounts 
                    SET total_requests = total_requests + ?,
                        total_likes = total_likes + ?
                    WHERE id = ?
                """, (
                    self.current_session['request_count'],
                    stats.get('likes_sent', 0),
                    account_id
                ))
                
                conn.commit()
                
        except Exception as e:
            logging.error(f"Error ending enhanced session: {e}")
    
    def _calculate_session_quality(self, stats: Dict) -> float:
        """Calculate session quality score based on various metrics"""
        score = 1.0
        
        # Penalty for errors
        if self.current_session['error_count'] > 0:
            error_rate = self.current_session['error_count'] / max(self.current_session['request_count'], 1)
            score -= error_rate * 0.5
        
        # Penalty for too many or too few actions
        likes_sent = stats.get('likes_sent', 0)
        if likes_sent == 0:
            score -= 0.3
        elif likes_sent > self.config['max_likes_per_session']:
            score -= 0.2
        
        # Bonus for matches
        matches = stats.get('matches_gained', 0)
        if matches > 0:
            score += min(matches * 0.1, 0.3)
        
        # Penalty for suspicious timing
        session_duration = (datetime.now() - self.current_session['start_time']).total_seconds()
        if session_duration < 300:  # Less than 5 minutes
            score -= 0.2
        elif session_duration > 3600:  # More than 1 hour
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _initialize_api(self, account: Dict) -> Optional[TinderApi]:
        """Initialize API with enhanced error handling"""
        try:
            api = TinderApi(
                auth_token=account['auth_token'],
                refresh_token=account['refresh_token'],
                persistent_device_id=account['persistent_device_id'],
                device_ram=account.get('device_ram', '5'),
                os_version=account.get('os_version', '34'),
                install_id=account['install_id'],
                appsflyer_id=account.get('appsflyer_id'),
                advertising_id=account.get('advertising_id'),
                proxy=account.get('proxy'),
                longitude=account.get('coordinates_lon'),
                latitude=account.get('coordinates_lat')
            )
            
            # Test authentication
            if not self.validate_authentication_enhanced(api, account['id']):
                return None
            
            return api
            
        except Exception as e:
            return None

    
    
    
    def process_single_account_enhanced(self, account: Dict):
        """Enhanced account processing with continuous swiping for accounts with likes"""
        # Store current account for error handling
        self._current_account = account
        
        account_id = account['id']
        device_id = account['device_id']
        city = account.get('assigned_city', 'Unknown')
        username = account.get('assigned_username', 'Unknown')
        
        print(f"\n🔄 Processing account {account_id} ({device_id[:8]}...)")
        print(f"   📍 City: {city}")
        print(f"   👤 Username: {username}")
        
        # Start enhanced session
        session_id = self.start_enhanced_session(account_id)
        if not session_id:
            print("   ❌ Failed to start session")
            return
        
        # Get initial database stats
        initial_total_likes, initial_likes_today = self.get_database_stats()
        
        # Calculate session parameters
        session_duration = random.randint(
            self.config.get('session_duration_min', 600),
            self.config.get('session_duration_max', 1800)
        )
        session_end_time = datetime.now() + timedelta(seconds=session_duration)
        
        # Initialize API with enhanced configuration
        api = self._initialize_api(account)
        if not api:
            print("   ❌ Account banned or authentication failed")
            self.end_enhanced_session(account_id, session_id, {})
            return
        
        # Initialize session stats early
        session_stats = {
            'likes_sent': 0,
            'passes_sent': 0,
            'matches_gained': 0,
            'users_processed': 0,
            'api_calls_made': 0,
            'phases_completed': []
        }
        
        try:
            # PHASE 1: STARTUP
            self.transition_session_phase(SessionPhase.STARTUP, account_id)
            startup_result = self.execute_request_pattern(api, 'startup', account_id, session_id)
            session_stats['api_calls_made'] += startup_result['requests_made']
            session_stats['phases_completed'].append('startup')
            
            if not startup_result['success'] or startup_result['errors'] > 2:
                print("   ❌ Startup phase failed")
                return
            
            # Check if account has Gold/Plus - this is critical
            profile_data = api.profile()
            if not profile_data:
                print("   ❌ Failed to get profile - account may be dead")
                self.end_enhanced_session(account_id, session_id, session_stats)
                return
            
            is_gold, gold_expires_at = self.check_gold_status(profile_data)
            
            if not is_gold:
                print(f"   ❌ Account is NOT GOLD - marking as non-working")
                print(f"   📊 Stats for {city}: Free account (no Gold/Plus subscription)")
                # Mark as banned since we only want Gold accounts
                self._mark_account_banned(account_id)
                self.end_enhanced_session(account_id, session_id, session_stats)
                return
            
            # NEW: Always check for new likes regardless of time
            liked_me_count = api.liked_me_count()
            if liked_me_count is not None and liked_me_count != account.get('liked_me_count', 0):
                # Update the count in database
                self._update_cached_liked_count(account_id, liked_me_count)
                print(f"   💕 Updated liked me count: {liked_me_count}")
            else:
                liked_me_count = account.get('liked_me_count', 0)
            
            print(f"   💛 Gold Status: Active (expires: {gold_expires_at[:10] if gold_expires_at else 'Unknown'})")
            
            # If no likes, check if we should check for new ones
            if liked_me_count == 0:
                if self.should_check_likes_for_account(account):
                    print(f"   🔍 Checking for new likes...")
                    liked_me_count = api.liked_me_count()
                    if liked_me_count is not None:
                        self.update_liked_me_check(account_id, liked_me_count)
                        if liked_me_count > 0:
                            print(f"   💕 Found {liked_me_count} new likes!")
                        else:
                            print(f"   💔 No likes yet")
                else:
                    print(f"   ⏭️  Skipping account - no likes to process")
                    # Still do profile update even if no likes
                    self.transition_session_phase(SessionPhase.PROFILE_UPDATE, account_id)
                    profile_updated = self.smart_update_profile_enhanced(api, account_id, account, session_id)
                    if profile_updated:
                        self.adaptive_delay('long', "after profile update", 1.5)
                    session_stats['phases_completed'].append('profile_update')
                    
                    self.end_enhanced_session(account_id, session_id, session_stats)
                    return
            
            # PHASE 2: PROFILE UPDATE (only if bio/prompt not set)
            # Check if profile needs update first
            if self._profile_needs_update(api, account):
                self.transition_session_phase(SessionPhase.PROFILE_UPDATE, account_id)
                profile_updated = self.smart_update_profile_enhanced(api, account_id, account, session_id)
                if profile_updated:
                    self.adaptive_delay('long', "after profile update", 1.5)
                session_stats['phases_completed'].append('profile_update')
            
            # PHASE 3: LIKING - PROCESS ALL LIKED_ME CONTINUOUSLY
            if self.config['like_users_who_liked_me'] and liked_me_count > 0:
                self.transition_session_phase(SessionPhase.LIKING, account_id)
                
                print(f"   🚀 CONTINUOUS SWIPING MODE - Processing {liked_me_count} likes")
                
                like_stats = self.process_all_liked_me_enhanced(
                    api, account_id, session_id, session_end_time
                )
                
                # Merge stats
                for key in ['likes_sent', 'passes_sent', 'matches_gained', 'users_processed']:
                    session_stats[key] += like_stats.get(key, 0)
                session_stats['api_calls_made'] += like_stats.get('api_calls_made', 0)
                session_stats['phases_completed'].append('liking')
            
            # Track username usage for this city if we processed users
            if session_stats['users_processed'] > 0:
                if username and username != 'Unknown' and city and city != 'Unknown':
                    self.track_username_usage(username, city, account_id)
                    self.check_username_completion(username)
            
            # Final session summary
            final_total_likes, final_likes_today = self.get_database_stats()
            total_matches = self._get_total_matches(account_id)
            
            print(f"\n   ✅ Session Complete for {city} ({username}):")
            print(f"      💛 Gold: Yes (expires {gold_expires_at[:10] if gold_expires_at else 'Unknown'})")
            print(f"      💕 Processed: {session_stats['users_processed']} users")
            print(f"      👍 Likes sent: {session_stats['likes_sent']}")
            print(f"      💘 New matches: {session_stats['matches_gained']}")
            print(f"      📊 Total matches all-time: {total_matches}")
            
        except Exception as e:
            print(f"   ❌ Enhanced processing error: {e}")
            logging.error(f"Processing error for account {account_id}: {e}")
            logging.error(traceback.format_exc())
            
        finally:
            # Always end the session
            self.end_enhanced_session(account_id, session_id, session_stats)
    
    def _profile_needs_update(self, api: TinderApi, account: Dict) -> bool:
        """Check if profile needs update without making unnecessary API calls"""
        try:
            # Get profile data (use cached if available)
            profile_data = api.profile()
            if not profile_data:
                return False
            
            user_data = profile_data.get("data", {}).get("user", {})
            current_bio = user_data.get("bio", "")
            current_prompts = user_data.get("user_prompts", {}).get("prompts", [])
            
            assigned_username = account.get('assigned_username')
            
            # Check bio
            if self.config['update_bio'] and self.config['bio'] and assigned_username and assigned_username != 'Unknown':
                target_bio = self.config['bio'].replace('%username%', assigned_username)
                if self._should_update_bio_fixed(current_bio, target_bio):
                    return True
            
            # Check prompts
            if self.config['add_prompt_to_profile'] and self.config['prompt_text'] and self.config['prompt_id'] and assigned_username and assigned_username != 'Unknown':
                target_prompt_text = self.config['prompt_text'].replace('%username%', assigned_username)
                if self._should_update_prompts(current_prompts, self.config['prompt_id'], target_prompt_text):
                    return True
            
            return False
        except:
            return False
        
        
        
    def validate_authentication_enhanced(self, api: TinderApi, account_id: int) -> bool:
        """Enhanced authentication validation with proper 401/403 handling"""
        try:
            # First try a simple profile request
            profile_data = api.profile()
            if profile_data:
                ban_score = self._check_ban_indicators(profile_data)
                
                if ban_score >= 0.8:
                    self._mark_account_banned(account_id)
                    return False
                
                return True
            
            # Check if we have a response object to examine status code
            if hasattr(api, '_last_response_status'):
                status_code = api._last_response_status
            else:
                # Try to get status from the API's last request
                status_code = getattr(api, 'last_status_code', None)
            
            # Handle 403 - Account banned
            if status_code == 403:
                logging.warning(f"Account {account_id} received 403 - marking as banned")
                self._mark_account_banned(account_id)
                return False
            
            # Handle 401 - Try refresh token
            if status_code == 401:
               # logging.info(f"Account {account_id} received 401 - attempting token refresh")
                auth_result = api.auth_login()
                if auth_result and auth_result.get("success"):
                  #  logging.info(f"Account {account_id} token refreshed successfully")
                    # Try profile again after refresh
                    profile_data = api.profile()
                    if profile_data:
                        return True
                    else:
                        # If still fails after refresh, check status again
                        if hasattr(api, '_last_response_status') and api._last_response_status == 403:
                            self._mark_account_banned(account_id)
                            return False
                
                # If refresh fails, mark as dead (not banned)
                #logging.warning(f"Account {account_id} token refresh failed - marking as dead")
                self._mark_account_dead_from_id(account_id, "Token refresh failed", "401 auth failure")
                return False
            
            # For any other failure, mark as dead
            self._mark_account_dead_from_id(account_id, "Profile check failed", f"Status: {status_code}")
            return False
            
        except Exception as e:
         #   logging.error(f"Authentication validation error for account {account_id}: {e}")
            self._mark_account_dead_from_id(account_id, "Auth validation exception", str(e))
            return False

    def import_tokens(self) -> int:
        """Import tokens with enhanced validation and support for simplified format"""
        if not os.path.exists('tokens.txt'):
            return 0
        
        imported_count = 0
        failed_tokens = []
        
        # Try different encodings
        content = None
        
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                with open('tokens.txt', 'r', encoding=encoding) as f:
                    lines = f.readlines()
                content = lines
                break
            except Exception as e:
                continue
        
        if not content:
            return 0
        
        try:
            for i, line in enumerate(content, 1):
                line = line.strip()
                
                # Remove BOM and problematic characters
                line = line.replace('\ufeff', '').replace('\x00', '')
                
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(':')
                
                if len(parts) < 3:
                    failed_tokens.append(line)
                    continue
                
                try:
                    print(f"DEBUG: Token has {len(parts)} parts: {parts}")
                    
                    if len(parts) >= 6 and len(parts) <= 10:
                        # CORRECTED SIMPLIFIED FORMAT: auth:persistentID:refresh:lat:long:proxy_parts...
                        auth_token = parts[0].strip()           # d229ef2e-bad2-4270-a1e4-2dbd954a12b2
                        persistent_device_id = parts[1].strip() # a560c124945a07ef  
                        refresh_token = parts[2].strip()        # eyJhbGciOiJIUzI1NiJ9...
                        
                        # Parse coordinates safely
                        try:
                            latitude = float(parts[3].strip()) if parts[3].strip() and parts[3].strip() != '0' else None    # 19.076090
                            longitude = float(parts[4].strip()) if parts[4].strip() and parts[4].strip() != '0' else None   # 72.877426
                        except (ValueError, IndexError):
                            latitude = None
                            longitude = None
                        
                        # Handle proxy - could be split across multiple parts due to colons
                        if len(parts) > 5:
                            proxy_parts = parts[5:]
                            proxy_combined = ':'.join(proxy_parts).strip()
                            proxy = proxy_combined if proxy_combined else None
                        else:
                            proxy = None
                        
                        # Generate missing IDs randomly
                        device_id = persistent_device_id  # Use persistent ID as device ID (a560c124945a07ef)
                        install_id = self._generate_install_id()
                        appsflyer_id = self._generate_appsflyer_id()
                        advertising_id = self._generate_advertising_id()
                        device_ram = self._generate_device_ram()
                        os_version = self._generate_os_version()
                        
                        print(f"   📋 Auth: {auth_token[:12]}...")
                        print(f"   📋 Device: {device_id}")
                        print(f"   📋 Refresh: {refresh_token[:12]}...")
                        print(f"   📋 Location: {latitude}, {longitude}")
                        print(f"   🌐 Proxy: {proxy[:50]}..." if proxy and len(proxy) > 50 else f"   🌐 Proxy: {proxy}")
                        
                    elif len(parts) == 5:
                        # SIMPLIFIED FORMAT WITHOUT PROXY: auth:persistentID:refresh:lat:long
                        auth_token = parts[0].strip()
                        persistent_device_id = parts[1].strip()
                        refresh_token = parts[2].strip()
                        latitude = float(parts[3].strip()) if parts[3].strip() else None
                        longitude = float(parts[4].strip()) if parts[4].strip() else None
                        proxy = None
                        
                        # Generate missing IDs randomly
                        device_id = persistent_device_id
                        install_id = self._generate_install_id()
                        appsflyer_id = self._generate_appsflyer_id()
                        advertising_id = self._generate_advertising_id()
                        device_ram = self._generate_device_ram()
                        os_version = self._generate_os_version()
                        
                    elif len(parts) >= 11:
                        # Enhanced format with location
                        auth_token = parts[0].strip()
                        refresh_token = parts[1].strip()
                        device_id = parts[2].strip()
                        persistent_device_id = parts[3].strip()
                        install_id = parts[4].strip()
                        appsflyer_id = parts[5].strip()
                        advertising_id = parts[6].strip()
                        device_ram = parts[7].strip()
                        os_version = parts[8].strip()
                        longitude = float(parts[9].strip()) if parts[9].strip() else None
                        latitude = float(parts[10].strip()) if parts[10].strip() else None
                        proxy = parts[11].strip() if len(parts) > 11 else None
                        
                    elif len(parts) >= 9:
                        # Enhanced format without location
                        auth_token = parts[0].strip()
                        refresh_token = parts[1].strip()
                        device_id = parts[2].strip()
                        persistent_device_id = parts[3].strip()
                        install_id = parts[4].strip()
                        appsflyer_id = parts[5].strip()
                        advertising_id = parts[6].strip()
                        device_ram = parts[7].strip()
                        os_version = parts[8].strip()
                        longitude = None
                        latitude = None
                        proxy = parts[9].strip() if len(parts) > 9 else None
                        
                    else:
                        # Legacy format - generate missing IDs with enhanced defaults
                        auth_token = parts[0].strip()
                        refresh_token = parts[1].strip()
                        device_id = parts[2].strip()
                        persistent_device_id = device_id
                        install_id = self._generate_install_id()
                        appsflyer_id = self._generate_appsflyer_id()
                        advertising_id = self._generate_advertising_id()
                        device_ram = self._generate_device_ram()
                        os_version = self._generate_os_version()
                        longitude = None
                        latitude = None
                        proxy = parts[3].strip() if len(parts) > 3 else None
                    
                    # Enhanced validation
                    if not self._validate_token_format(auth_token, refresh_token, device_id):
                        failed_tokens.append(line)
                        continue
                    
                    if self.process_single_token_enhanced(
                        auth_token, refresh_token, device_id, persistent_device_id,
                        install_id, appsflyer_id, advertising_id, device_ram, os_version,
                        longitude, latitude, proxy
                    ):
                        imported_count += 1
                    else:
                        failed_tokens.append(line)
                    
                    # Enhanced delay between imports
                    self.adaptive_delay('medium', "between token imports")
                    
                except Exception as e:
                    failed_tokens.append(line)
                    logging.error(f"Error processing token: {e}")
            
            # Update tokens.txt with enhanced format
            if failed_tokens:
                with open('tokens.txt', 'w', encoding='utf-8') as f:
                    f.write("# Failed tokens - please check format\n")
                    f.write("# Supported formats:\n")
                    f.write("# Simplified: auth_token:persistent_device_id:refresh_token:lat:lon:proxy\n")
                    f.write("# Enhanced: auth_token:refresh_token:device_id:persistent_device_id:install_id:appsflyer_id:advertising_id:device_ram:os_version:long:lat:proxy\n")
                    for failed_token in failed_tokens:
                        f.write(failed_token + '\n')
            else:
                with open('tokens.txt', 'w', encoding='utf-8') as f:
                    f.write("# All tokens imported successfully with enhanced processing\n")
            
        except Exception as e:
            logging.error(f"Error in enhanced token import: {e}")
        
        return imported_count

    def _generate_install_id(self) -> str:
        """Generate realistic install ID"""
        # Real Tinder install IDs are base64-like strings
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        return ''.join(random.choice(chars) for _ in range(11))

    def _generate_appsflyer_id(self) -> str:
        """Generate realistic AppsFlyer ID"""
        # Format: timestamp-randomnumber
        timestamp = int(time.time() * 1000)
        random_num = random.randint(1000000000000000000, 9999999999999999999)
        return f"{timestamp}-{random_num}"

    def _generate_advertising_id(self) -> str:
        """Generate realistic advertising ID (UUID format)"""
        return str(uuid.uuid4())

    def _generate_device_ram(self) -> str:
        """Generate realistic device RAM values"""
        # Common Android device RAM sizes
        ram_options = ["3", "4", "5", "6", "8", "12", "16"]
        return random.choice(ram_options)

    def _generate_os_version(self) -> str:
        """Generate realistic Android OS version"""
        # Common Android API levels (Android 8.0 to 14)
        api_levels = ["26", "27", "28", "29", "30", "31", "32", "33", "34"]
        return random.choice(api_levels)






    def _mark_account_banned(self, account_id: int):
        """Mark account as banned, move token to banned.txt, and get matches for output"""
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                
                # Get account info before marking as banned
                cursor.execute("""
                    SELECT assigned_city, auth_token, refresh_token, device_id, persistent_device_id,
                        install_id, appsflyer_id, advertising_id, device_ram, os_version,
                        coordinates_lon, coordinates_lat, proxy FROM accounts WHERE id = ?
                """, (account_id,))
                result = cursor.fetchone()
                
                if not result:
                    return
                    
                (city, auth_token, refresh_token, device_id, persistent_device_id,
                install_id, appsflyer_id, advertising_id, device_ram, os_version,
                coordinates_lon, coordinates_lat, proxy) = result
                
                city = city or "Unknown"
                
                # Get total matches
                matches = self._get_total_matches(account_id)
                
                # Mark account as banned (change status from 'active' to 'banned')
                cursor.execute("""
                    UPDATE accounts 
                    SET status = 'banned', ban_score = 1.0, last_error = ?, last_error_time = ?
                    WHERE id = ?
                """, ("Account banned - 403 response", datetime.now(), account_id))
                
                conn.commit()
                
                # Move token to banned.txt
                self._move_token_to_file(
                    auth_token, refresh_token, device_id, persistent_device_id,
                    install_id, appsflyer_id, advertising_id, device_ram, os_version,
                    coordinates_lon, coordinates_lat, proxy, "banned.txt", 
                    f"BANNED - {city} - {matches} matches"
                )
                
                logging.warning(f"Account {account_id} ({city}) marked as BANNED with {matches} matches")
                
        except Exception as e:
            logging.error(f"Error marking account as banned: {e}")

    def _mark_account_dead_from_id(self, account_id: int, reason: str, details: str):
        """Mark account as dead by account ID and move token to dead.txt"""
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                
                # Get account info
                cursor.execute("""
                    SELECT auth_token, refresh_token, device_id, persistent_device_id, assigned_city,
                        install_id, appsflyer_id, advertising_id, device_ram, os_version,
                        coordinates_lon, coordinates_lat, proxy 
                    FROM accounts WHERE id = ?
                """, (account_id,))
                result = cursor.fetchone()
                
                if result:
                    (auth_token, refresh_token, device_id, persistent_device_id, city,
                    install_id, appsflyer_id, advertising_id, device_ram, os_version,
                    coordinates_lon, coordinates_lat, proxy) = result
                    
                    # Use existing method to mark as dead in database
                    self.mark_account_dead_enhanced(
                        auth_token, refresh_token, device_id, persistent_device_id, reason, details
                    )
                    
                    # Move token to dead.txt
                    self._move_token_to_file(
                        auth_token, refresh_token, device_id, persistent_device_id,
                        install_id, appsflyer_id, advertising_id, device_ram, os_version,
                        coordinates_lon, coordinates_lat, proxy, "dead.txt", 
                        f"DEAD - {reason}: {details}"
                    )
                    
                  #  logging.warning(f"Account {account_id} ({city}) marked as dead: {reason}")
                
        except Exception as e:
            logging.error(f"Error marking account dead from ID: {e}")

    def mark_account_dead_enhanced(self, auth_token: str, refresh_token: str, device_id: str,
                                persistent_device_id: str, reason: str, details: str):
        """Enhanced account death marking with better tracking and token file management"""
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                
                # Get additional account info for file moving
                cursor.execute("""
                    SELECT install_id, appsflyer_id, advertising_id, device_ram, os_version,
                        coordinates_lon, coordinates_lat, proxy, assigned_city
                    FROM accounts WHERE device_id = ?
                """, (device_id,))
                account_info = cursor.fetchone()
                
                # Create dead_accounts table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dead_accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        auth_token TEXT,
                        refresh_token TEXT,
                        device_id TEXT,
                        persistent_device_id TEXT,
                        reason TEXT,
                        error_details TEXT,
                        marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Insert into dead accounts
                cursor.execute("""
                    INSERT INTO dead_accounts 
                    (auth_token, refresh_token, device_id, persistent_device_id, reason, error_details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (auth_token, refresh_token, device_id, persistent_device_id, reason, details))
                
                # Also mark in main accounts table if exists
                cursor.execute("""
                    UPDATE accounts 
                    SET status = 'dead', ban_score = 1.0, last_error = ?, last_error_time = ?
                    WHERE device_id = ?
                """, (f"{reason}: {details}", datetime.now(), device_id))
                
                conn.commit()
                
                # Move token to dead.txt if we have account info
                if account_info:
                    (install_id, appsflyer_id, advertising_id, device_ram, os_version,
                    coordinates_lon, coordinates_lat, proxy, city) = account_info
                    
                    self._move_token_to_file(
                        auth_token, refresh_token, device_id, persistent_device_id,
                        install_id, appsflyer_id, advertising_id, device_ram, os_version,
                        coordinates_lon, coordinates_lat, proxy, "dead.txt", 
                        f"DEAD - {reason}: {details}"
                    )
                
           # logging.warning(f"Enhanced account marked as dead: {device_id} - {reason}")
            
        except Exception as e:
            logging.error(f"Error marking account dead (enhanced): {e}")

    def _move_token_to_file(self, auth_token: str, refresh_token: str, device_id: str,
                        persistent_device_id: str, install_id: str, appsflyer_id: str,
                        advertising_id: str, device_ram: str, os_version: str,
                        coordinates_lon: Optional[float], coordinates_lat: Optional[float],
                        proxy: Optional[str], target_file: str, comment: str):
        """Move token from tokens.txt to target file and remove from tokens.txt"""
        try:
            # Reconstruct the token line
            token_parts = [
                auth_token, refresh_token, device_id, persistent_device_id,
                install_id, appsflyer_id, advertising_id, device_ram, os_version
            ]
            
            if coordinates_lon is not None and coordinates_lat is not None:
                token_parts.extend([str(coordinates_lon), str(coordinates_lat)])
            
            if proxy:
                token_parts.append(proxy)
            
            token_line = ":".join(token_parts)
            
            # Remove from tokens.txt
            self._remove_token_from_file(device_id, auth_token)
            
            # Add to target file with timestamp and comment
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            commented_line = f"# {timestamp} - {comment}\n{token_line}\n"
            
            with open(target_file, 'a', encoding='utf-8') as f:
                f.write(commented_line)
            
          #  logging.info(f"Token moved to {target_file}: {device_id[:8]}...")
            
        except Exception as e:
            logging.error(f"Error moving token to {target_file}: {e}")

    def _remove_token_from_file(self, device_id: str, auth_token: str = None):
        """
        Remove token from tokens.txt by matching device_id OR auth_token
        """
        try:
            if not os.path.exists("tokens.txt"):
                logging.warning("tokens.txt does not exist")
                return
            
            # Read all lines
            with open("tokens.txt", 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find lines to keep (not matching our tokens)
            lines_to_keep = []
            removed_count = 0
            
            for line in lines:
                original_line = line
                line_content = line.strip()
                
                # Skip empty lines and comments
                if not line_content or line_content.startswith('#'):
                    lines_to_keep.append(original_line)
                    continue
                
                # Check if this line contains our device_id or auth_token
                should_remove = False
                
                # Split by : to check tokens
                parts = line_content.split(':')
                if len(parts) >= 3:
                    # Check different token formats
                    # For simplified format: auth:persistent_device_id:refresh:...
                    # For full format: auth:refresh:device_id:persistent_device_id:...
                    
                    # Try to find device_id in different positions
                    if device_id:
                        # Check if device_id matches in any position
                        for part in parts:
                            if part.strip() == device_id:
                                should_remove = True
                                break
                    
                    # Also check auth_token if provided
                    if not should_remove and auth_token and len(auth_token) > 8:
                        # Check if auth token matches (compare first part)
                        if parts[0].strip().startswith(auth_token[:8]):
                            should_remove = True
                
                if should_remove:
                    removed_count += 1
                    logging.info(f"Removing token from tokens.txt: {line_content[:50]}...")
                else:
                    lines_to_keep.append(original_line)
            
            # Write back the filtered lines
            with open("tokens.txt", 'w', encoding='utf-8') as f:
                f.writelines(lines_to_keep)
            
            if removed_count > 0:
                logging.info(f"✅ Removed {removed_count} token(s) from tokens.txt")
            else:
                logging.warning(f"⚠️ No tokens found to remove for device_id: {device_id}")
                
        except Exception as e:
            logging.error(f"Error removing token from file: {e}")

    
    
    def process_single_token_enhanced(self, auth_token: str, refresh_token: str, device_id: str,
                            persistent_device_id: str, install_id: str, appsflyer_id: str,
                            advertising_id: str, device_ram: str, os_version: str, 
                            longitude: Optional[float], latitude: Optional[float],
                            proxy: Optional[str]) -> bool:
        """Enhanced token processing with proper 401/403 handling and file management"""
        try:
            # Check if account already exists
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, ban_score, status FROM accounts WHERE device_id = ?", (device_id,))
                existing = cursor.fetchone()
                
                if existing:
                    account_id, ban_score, status = existing
                    if status == 'banned' or (ban_score and ban_score >= 0.8):
                        logging.info(f"Account {device_id[:8]}... already banned in database")
                        return False
                    elif status == 'active':
                        logging.info(f"Account {device_id[:8]}... already active in database")
                        return True
            
            # Create enhanced TinderApi instance
            api = TinderApi(
                auth_token=auth_token,
                refresh_token=refresh_token,
                persistent_device_id=persistent_device_id,
                device_ram=device_ram,
                os_version=os_version,
                install_id=install_id,
                appsflyer_id=appsflyer_id,
                advertising_id=advertising_id,
                longitude=longitude,
                latitude=latitude,
                proxy=proxy
            )
            
            # Enhanced startup simulation
            api.buckets()
            self.adaptive_delay('short', "after buckets")
            
            api.get_updates()
            self.adaptive_delay('medium', "after updates")
            
            # Phase 2: Authentication with enhanced validation
            auth_result = api.auth_login()
            
            # Always check the last response status after auth attempt
            last_status = getattr(api, '_last_response_status', None)
            
            if last_status == 403:
                logging.warning(f"Token {device_id[:8]}... received 403 during auth - BANNED")
                self._move_token_to_file(
                    auth_token, refresh_token, device_id, persistent_device_id,
                    install_id, appsflyer_id, advertising_id, device_ram, os_version,
                    longitude, latitude, proxy, "banned.txt", 
                    "BANNED during import - 403 forbidden during auth"
                )
                return False
            elif last_status == 401:
                logging.warning(f"Token {device_id[:8]}... received 401 during auth - DEAD TOKEN")
                self._move_token_to_file(
                    auth_token, refresh_token, device_id, persistent_device_id,
                    install_id, appsflyer_id, advertising_id, device_ram, os_version,
                    longitude, latitude, proxy, "dead.txt", 
                    "DEAD during import - 401 unauthorized during auth"
                )
                return False
            elif not auth_result or not auth_result.get("success"):
                # For any other auth failure, mark as dead
                self._move_token_to_file(
                    auth_token, refresh_token, device_id, persistent_device_id,
                    install_id, appsflyer_id, advertising_id, device_ram, os_version,
                    longitude, latitude, proxy, "dead.txt", 
                    f"DEAD during import - Auth failed with status {last_status}: {str(auth_result)}"
                )
                return False
            
            # Update token if changed
            if auth_result.get("auth_token") and auth_result["auth_token"] != auth_token:
                auth_token = auth_result["auth_token"]
                api.auth_token = auth_token
            
            self.adaptive_delay('medium', "after auth")
            
            # Phase 3: Enhanced profile validation
            profile_data = api.profile()
            
            # Always check the last response status after profile attempt
            profile_status = getattr(api, '_last_response_status', None)
            
            if profile_status == 403:
                logging.warning(f"Token {device_id[:8]}... received 403 during profile fetch - BANNED")
                self._move_token_to_file(
                    auth_token, refresh_token, device_id, persistent_device_id,
                    install_id, appsflyer_id, advertising_id, device_ram, os_version,
                    longitude, latitude, proxy, "banned.txt", 
                    "BANNED during import - 403 forbidden during profile fetch"
                )
                return False
            elif not profile_data:
                self._move_token_to_file(
                    auth_token, refresh_token, device_id, persistent_device_id,
                    install_id, appsflyer_id, advertising_id, device_ram, os_version,
                    longitude, latitude, proxy, "dead.txt", 
                    f"DEAD during import - Profile check failed with status {profile_status}"
                )
                return False
            
            # Enhanced ban detection
            ban_score = self._check_ban_indicators(profile_data)
            if ban_score >= self.config.get('ban_detection_sensitivity', 0.8):
                self._move_token_to_file(
                    auth_token, refresh_token, device_id, persistent_device_id,
                    install_id, appsflyer_id, advertising_id, device_ram, os_version,
                    longitude, latitude, proxy, "banned.txt", 
                    f"BANNED during import - Enhanced ban detection: Ban score: {ban_score}"
                )
                return False
            
            # Extract enhanced account info
            user_data = profile_data.get("data", {}).get("user", {})
            user_id = user_data.get("_id")
            
            # Enhanced Gold status check
            is_gold, gold_expires_at = self.check_gold_status(profile_data)
            
            # IMPORTANT: Check if account has Gold, if not, don't import
            if not is_gold:
                logging.warning(f"Account {device_id[:8]}... is FREE account - not importing")
                self._move_token_to_file(
                    auth_token, refresh_token, device_id, persistent_device_id,
                    install_id, appsflyer_id, advertising_id, device_ram, os_version,
                    longitude, latitude, proxy, "free_accounts.txt", 
                    "FREE ACCOUNT - No Gold/Plus subscription"
                )
                return False
            
            # Enhanced liked me count
            liked_me_count = api.liked_me_count() or 0
            
            # Enhanced location assignment - FIXED
            # Enhanced location assignment - FIXED to use passport location
            current_location = api.get_current_passport_location()
            assigned_city = None
            coordinates = None

            # Always use passport location if available
            if current_location:
                # current_location returns (lat, lon, city_name)
                coordinates = (current_location[0], current_location[1])
                assigned_city = current_location[2]
                logging.info(f"Using current passport location: {assigned_city}")
            elif self.cities and is_gold:
                # Assign new random city from cities.txt
                city_info = random.choice(self.cities)
                assigned_city = f"{city_info['city']}, {city_info['country']}"
                coordinates = (city_info['lat'], city_info['lon'])
                
                self.adaptive_delay('long', "before setting location")
                
                if api.set_passport_location(city_info['lat'], city_info['lon']):
                    logging.info(f"Set new passport location to {assigned_city}")
                else:
                    logging.warning(f"Failed to set passport location to {assigned_city}")
            else:
                # Fallback - this should rarely happen
                assigned_city = "Unknown Location"
                coordinates = (latitude, longitude) if latitude and longitude else None

            # The longitude/latitude from token is just for the API, not for display
            # assigned_city should ALWAYS be the passport location name
            
            # Enhanced username assignment
            assigned_username = self.assign_username_enhanced(assigned_city)
            
            # Create enhanced account record
            account_id = self.create_account_record_enhanced(
                auth_token, refresh_token, device_id, persistent_device_id,
                install_id, appsflyer_id, advertising_id, device_ram, os_version, proxy,
                user_id, assigned_city, assigned_username, coordinates,
                is_gold, liked_me_count, gold_expires_at, ban_score
            )
            print(assigned_city)
            
            if account_id:
                print(f"✅ Successfully imported GOLD account: {assigned_city} ({device_id[:8]}...)")
                print(f"   💛 Gold expires: {gold_expires_at[:10] if gold_expires_at else 'Unknown'}")
                print(f"   💕 Liked me count: {liked_me_count}")
                # Only remove from tokens.txt if successfully imported
                self._remove_token_from_file(device_id, auth_token)
                return True
            else:
                logging.error(f"Failed to create account record for {device_id[:8]}...")
                return False
                
        except Exception as e:
            logging.error(f"Error processing token {device_id[:8]}...: {e}")
            logging.error(traceback.format_exc())
            self._move_token_to_file(
                auth_token, refresh_token, device_id, persistent_device_id,
                install_id, appsflyer_id, advertising_id, device_ram, os_version,
                longitude, latitude, proxy, "dead.txt", 
                f"DEAD during import - Enhanced processing error: {str(e)}"
            )
            return False

    def track_username_usage(self, username: str, city: str, account_id: int):
        """Track username usage for city"""
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                
                # Create tracking table if doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS username_city_tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        city TEXT NOT NULL,
                        account_id INTEGER,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (account_id) REFERENCES accounts(id)
                    )
                """)
                
                # Insert tracking record
                cursor.execute("""
                    INSERT INTO username_city_tracking (username, city, account_id)
                    VALUES (?, ?, ?)
                """, (username, city, account_id))
                
                conn.commit()
                
        except Exception as e:
            logging.error(f"Error tracking username usage: {e}")

    def check_username_completion(self, username: str):
        """Check if username has been used for all allowed cities and update files"""
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                
                # Get all cities used by this username
                cursor.execute("""
                    SELECT DISTINCT city FROM username_city_tracking 
                    WHERE username = ?
                """, (username,))
                
                cities_used = cursor.fetchall()
                cities_count = len(cities_used)
                
                if cities_count >= self.config['tinders_per_username']:
                    # Username has been used enough times
                    # Write to usernames_done.txt
                    with open('usernames_done.txt', 'a', encoding='utf-8') as f:
                        for city_row in cities_used:
                            city = city_row[0]
                            f.write(f"{username},{city}\n")
                    
                    # Remove from usernames.txt
                    self._remove_username_from_file(username)
                    
                    # Remove from loaded usernames
                    if username in self.usernames:
                        self.usernames.remove(username)
                    
                    logging.info(f"Username '{username}' completed {cities_count} cities and moved to usernames_done.txt")
                    return True
                    
        except Exception as e:
            logging.error(f"Error checking username completion: {e}")
        
        return False

    def _remove_username_from_file(self, username: str):
        """Remove username from usernames.txt"""
        try:
            if not os.path.exists('usernames.txt'):
                return
            
            with open('usernames.txt', 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Filter out the username
            new_lines = []
            removed = False
            for line in lines:
                line_content = line.strip()
                if line_content and not line_content.startswith('#'):
                    if line_content == username:
                        removed = True
                        continue
                new_lines.append(line)
            
            # Write back
            with open('usernames.txt', 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            if removed:
                logging.info(f"Removed username '{username}' from usernames.txt")
                
        except Exception as e:
            logging.error(f"Error removing username from file: {e}")





    def _update_ban_score(self, account_id: int, ban_score: float):
        """Update account ban score in database"""
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE accounts 
                    SET ban_score = ?, last_ban_check = ?
                    WHERE id = ?
                """, (ban_score, datetime.now(), account_id))
                
                # Log ban indicator
                cursor.execute("""
                    INSERT INTO ban_indicators 
                    (account_id, indicator_type, indicator_value, severity)
                    VALUES (?, ?, ?, ?)
                """, (account_id, 'automated_detection', 'high_ban_score', ban_score))
                
                conn.commit()
        except Exception as e:
            logging.error(f"Error updating ban score: {e}")
    
    
    def smart_update_profile_enhanced(self, api: TinderApi, account_id: int, account: Dict, session_id: int) -> bool:
        """Enhanced profile update with no username dependency"""
        try:
            # Get current profile with timing
            start_time = time.time()
            profile_data = api.profile_cache if hasattr(api, 'profile_cache') and api.profile_cache else api.profile()
            if not profile_data:
                print("     ❌ Failed to get profile data")
                return False
            
            response_time = int((time.time() - start_time) * 1000)
            self.log_enhanced_activity(account_id, session_id, 'profile_check', None, True,
                                    response_time, 'profile_fetch', 
                                    self.current_session['phase'].value, {'full_profile': True})
            
            user_data = profile_data.get("data", {}).get("user", {})
            current_bio = user_data.get("bio", "")
            current_prompts = user_data.get("user_prompts", {}).get("prompts", [])
            
            updates_made = False
            assigned_username = account.get('assigned_username')
            
            # Bio update - only if we have a username
            if self.config['update_bio'] and self.config['bio'] and assigned_username and assigned_username != 'Unknown':
                target_bio = self.config['bio']
                if '%username%' in target_bio:
                    target_bio = target_bio.replace('%username%', assigned_username)
                
                print(f"     📄 Current bio: '{current_bio}'")
                print(f"     📝 Target bio: '{target_bio}'")
                
                if self._should_update_bio_fixed(current_bio, target_bio):
                    print(f"     📝 Updating bio...")
                    
                    start_time = time.time()
                    result = api.update_bio(target_bio)
                    response_time = int((time.time() - start_time) * 1000)
                    
                    success = result and result.get('success', False)
                    self.log_enhanced_activity(account_id, session_id, 'bio_update', None, success,
                                            response_time, 'profile_update',
                                            self.current_session['phase'].value,
                                            {'old_bio': current_bio, 'new_bio': target_bio})
                    
                    if success:
                        print("     ✅ Bio updated successfully")
                        updates_made = True
                        self.adaptive_delay('medium', "after bio update")
                    else:
                        print("     ❌ Bio update failed")
                else:
                    print(f"     ✅ Bio already correct")
            
            # Prompt update - only if we have a username
            if self.config['add_prompt_to_profile'] and self.config['prompt_text'] and self.config['prompt_id'] and assigned_username and assigned_username != 'Unknown':
                target_prompt_text = self.config['prompt_text']
                if '%username%' in target_prompt_text:
                    target_prompt_text = target_prompt_text.replace('%username%', assigned_username)
                
                print(f"     💬 Target prompt: '{target_prompt_text}' (ID: {self.config['prompt_id']})")
                
                if current_prompts:
                    print("     📋 Current prompts:")
                    for prompt in current_prompts:
                        prompt_id = prompt.get("id", "unknown")
                        prompt_text = prompt.get("answer_text", "")
                        print(f"        - ID: {prompt_id}, Text: '{prompt_text}'")
                else:
                    print("     📋 No current prompts")
                
                if self._should_update_prompts(current_prompts, self.config['prompt_id'], target_prompt_text):
                    print(f"     💬 Updating prompt...")
                    
                    start_time = time.time()
                    result = api.process_prompt(self.config['prompt_id'], target_prompt_text)
                    response_time = int((time.time() - start_time) * 1000)
                    
                    success = result and result.get('success', False)
                    self.log_enhanced_activity(account_id, session_id, 'prompt_update', None, success,
                                            response_time, 'profile_update',
                                            self.current_session['phase'].value,
                                            {'prompt_id': self.config['prompt_id'], 'prompt_text': target_prompt_text})
                    
                    if success:
                        print("     ✅ Prompt updated successfully")
                        updates_made = True
                        self.adaptive_delay('medium', "after prompt update")
                    else:
                        print("     ❌ Prompt update failed")
                else:
                    print("     ✅ Prompt already set correctly")
            
            return updates_made
            
        except Exception as e:
            logging.error(f"Error in enhanced profile update: {e}")
            logging.error(traceback.format_exc())
            return False


    def _should_update_bio_fixed(self, current_bio: str, target_bio: str) -> bool:
        """FIXED bio update decision logic"""
        # If no current bio and we have a target, update
        if not current_bio and target_bio:
            return True
        
        # If current bio contains placeholder, update
        if '%username%' in current_bio:
            return True
        
        # Normalize for comparison (strip whitespace and make lowercase)
        current_normalized = current_bio.strip().lower()
        target_normalized = target_bio.strip().lower()
        
        # If they're exactly the same, no update needed
        if current_normalized == target_normalized:
            return False
        
        # If current bio is very short or generic, update
        if len(current_normalized) < 10:
            return True
        
        # If target bio is in config and different from current, update
        if target_normalized and current_normalized != target_normalized:
            return True
        
        return False
    
    def _should_update_prompts(self, current_prompts: List, target_prompt_id: str, target_text: str) -> bool:
        """Sophisticated prompt update decision logic"""
        for prompt in current_prompts:
            prompt_id = prompt.get("id")
            prompt_text = prompt.get("answer_text", "")
            
            if prompt_id == target_prompt_id:
                if not prompt_text or '%username%' in prompt_text:
                    return True
                
                # Check if text is substantially different
                if prompt_text.strip().lower() == target_text.strip().lower():
                    return False
        
        # Prompt doesn't exist or needs update
        return True
    
    def simulate_browsing_behavior(self, api: TinderApi, account_id: int, session_id: int):
        """Simulate realistic browsing behavior"""
        print("     👀 Simulating browsing behavior...")
        
        # Get some recommendations
        for i in range(random.randint(1, 2)):
            start_time = time.time()
            recommendations = api.get_recommendations()
            response_time = int((time.time() - start_time) * 1000)
            
            success = recommendations is not None
            self.log_enhanced_activity(account_id, session_id, 'browse_recommendations', None, success,
                                     response_time, 'browsing', self.current_session['phase'].value,
                                     {'rec_count': len(recommendations) if recommendations else 0})
            
            if success and recommendations:
                print(f"     📱 Browsed {len(recommendations)} recommendations")
                
                # Simulate viewing time
                time.sleep(random.randrange(0.5,4))
            else:
                print("     ⚠️  No recommendations available")
                break
            
            # Random delay between browsing sessions
            if i < 3:
                self.adaptive_delay('short', "between browsing")
    



    def process_all_liked_me_enhanced(self, api: TinderApi, account_id: int, session_id: int, session_end_time: datetime) -> Dict:
        """Process ALL liked_me users with dual delay system"""
        stats = {
            'users_processed': 0,
            'likes_sent': 0,
            'passes_sent': 0,
            'matches_gained': 0,
            'api_calls_made': 0,
            'cycles_completed': 0,
            'total_available': 0
        }
        
        try:
            # Initial status check
            for i in range(random.randint(1,3)):  # Triple pattern
                liked_me_count = api.liked_me_count()
                stats['api_calls_made'] += 1
                
                if liked_me_count is not None:
                    stats['total_available'] = liked_me_count
            
            if stats['total_available'] == 0:
                # Update cached count to 0 after processing
                self._update_cached_liked_count(account_id, 0)
                return stats
            
            # Process ALL users with dual delay system
            cycle_number = 0
            page_token = None
            processed_user_ids = set()
            
            while datetime.now() < session_end_time and self.running:
                cycle_number += 1
                
                # Get batch
                batch_start = time.time()
                if page_token:
                    liked_users = api.liked_me(self.config.get('liked_me_count_per_request', 100), page_token)
                else:
                    liked_users = api.liked_me(self.config.get('liked_me_count_per_request', 100))
                
                batch_time = int((time.time() - batch_start) * 1000)
                stats['api_calls_made'] += 1
                
                # DELAY 1: After each page fetch
                page_delay = self.config.get('delay_after_page_fetch', 0.5)
                time.sleep(page_delay)
                
                if not liked_users:
                    break
                
                # Filter out already processed users
                new_users = []
                for user_data in liked_users:
                    user = user_data.get("user", {})
                    user_id = user.get("_id")
                    if user_id and user_id not in processed_user_ids:
                        new_users.append(user_data)
                        processed_user_ids.add(user_id)
                
                if not new_users:
                    break
                
                self.log_enhanced_activity(account_id, session_id, 'liked_me_batch', None, True,
                                        batch_time, 'liked_me_fetch', self.current_session['phase'].value,
                                        {'batch_size': len(new_users), 'cycle': cycle_number})
                
                # Process each user
                batch_likes = 0
                batch_passes = 0
                batch_matches = 0
                
                for i, user_data in enumerate(new_users, 1):
                    if datetime.now() >= session_end_time or not self.running:
                        break
                    
                    # Process single user
                    result = self._process_single_liked_user(api, account_id, session_id, user_data, i, len(new_users))
                    
                    if result['action'] == 'like':
                        batch_likes += 1
                        if result['matched']:
                            batch_matches += 1
                    elif result['action'] == 'pass':
                        batch_passes += 1
                    
                    stats['users_processed'] += 1
                    
                    # Check session limits
                    if stats['likes_sent'] + batch_likes >= self.config['max_likes_per_session']:
                        break
                    
                    # DELAY 2: Between each like/action
                    like_delay = self.config.get('delay_between_likes', 0.1)
                    if result['action'] in ['like', 'pass']:
                        time.sleep(like_delay)
                
                # Update stats
                stats['likes_sent'] += batch_likes
                stats['passes_sent'] += batch_passes
                stats['matches_gained'] += batch_matches
                stats['cycles_completed'] += 1
                
                print(f"     📈 TOTAL PROGRESS: {stats['users_processed']}/{stats['total_available']} users processed")
                
                # Check if we should continue
                if stats['likes_sent'] >= self.config['max_likes_per_session']:
                    break
                
                if not self.config.get('process_all_liked_me', True):
                    break
                
                # Check if we've processed all available users
                remaining_count = stats['total_available'] - stats['users_processed']
                if remaining_count <= 0:
                    break
                
                page_token = None  # Reset for next iteration
            
            # After processing all users, update the cached count to reflect remaining
            remaining_count = stats['total_available'] - stats['users_processed']
            self._update_cached_liked_count(account_id, max(0, remaining_count))
            
            return stats
            
        except Exception as e:
            logging.error(f"Enhanced liked_me processing error: {e}")
            return stats


    def _update_cached_liked_count(self, account_id: int, count: int):
            """Update only the cached liked_me count without updating check timestamp"""
            try:
                with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE account_status 
                        SET liked_me_count = ?
                        WHERE account_id = ?
                    """, (count, account_id))
                    conn.commit()
            except Exception as e:
                logging.error(f"Error updating cached liked count: {e}")

    def _process_single_liked_user(self, api: TinderApi, account_id: int, session_id: int, 
                            user_data: Dict, position: int, total: int) -> Dict:
        """Process a single liked_me user with NO DELAYS"""
        result = {'action': None, 'matched': False, 'success': False}
        
        try:
            user = user_data.get("user", {})
            user_id = user.get("_id")
            
            if not user_id:
                return result
            
            # Extract enhanced data
            photos = user.get("photos", [])
            photo_id = photos[0].get("id") if photos else None
            content_hash = user_data.get("content_hash")
            s_number = user_data.get("s_number")
            
            # LIKE ALL USERS - NO PASS PROBABILITY
            # Like with timing
            start_time = time.time()
            success = api.like_user(
                user_id=user_id,
                photo_id=photo_id,
                content_hash=content_hash,
                s_number=s_number,
                user_traveling=self.config['user_traveling_in_likes']
            )
            response_time = int((time.time() - start_time) * 1000)
            
            # Check for match
            matched = success == "match"
            actual_success = success is not False
            
            result = {'action': 'like', 'matched': matched, 'success': actual_success}
            
            # Log activity
            self.log_enhanced_activity(account_id, session_id, 'like', user_id, actual_success,
                                    response_time, 'liked_me_processing', 
                                    self.current_session['phase'].value,
                                    {'photo_id': photo_id, 's_number': s_number, 'matched': matched,
                                    'position': position, 'total': total})
            
            if matched:
                # Get updates after match (realistic behavior) - but no delay
                api.get_updates(include_nudge=True)
            
            # Update session action count
            self.current_session['actions_count'] += 1
            
            return result
            
        except Exception as e:
            logging.error(f"Error processing liked user {user_id}: {e}")
            return result 
                        
                                

     
    def _print_detailed_account_status(self, all_accounts: List[Dict]):
        """Print detailed status of why accounts aren't ready"""
        print(f"Total accounts in database: {len(all_accounts)}")
        
        not_ready_reasons = {
            'daily_limit': 0,
            'not_swipe_time': 0,
            'cooldown': 0,
            'high_error_rate': 0,
            'no_gold': 0
        }
        
        for account in all_accounts:
            account_id = account['id']
            city = account.get('assigned_city', 'Unknown')
            
            # Check why not ready
            if self.check_daily_like_limit(account_id):
                not_ready_reasons['daily_limit'] += 1
                print(f"   • {city}: Hit daily like limit")
            elif not self.is_in_swipe_time(account):
                not_ready_reasons['not_swipe_time'] += 1
                print(f"   • {city}: Outside swipe time window")
            elif self.needs_session_cooldown(account):
                not_ready_reasons['cooldown'] += 1
                last_session = account.get('last_session_end')
                if last_session:
                    print(f"   • {city}: In cooldown (last session: {last_session})")
            else:
                # Check for high error rate
                total_sessions = account.get('session_count', 0)
                if total_sessions > 5:
                    error_rate = account.get('error_count', 0) / total_sessions
                    if error_rate > 0.3:
                        not_ready_reasons['high_error_rate'] += 1
                        print(f"   • {city}: High error rate ({error_rate:.1%})")
        
        print("\nSummary of not-ready reasons:")
        for reason, count in not_ready_reasons.items():
            if count > 0:
                print(f"   - {reason.replace('_', ' ').title()}: {count} accounts")
     

    def run_enhanced(self):
        """Enhanced main bot loop with no username blocking"""
        
        # Initial username load - but don't block if empty
        self.usernames = self.load_usernames()
        if not self.usernames:
            print("⚠️  WARNING: No usernames found in usernames.txt")
            print("   Accounts will process but bio/prompts won't be updated")
            self.usernames = []  # Empty list instead of returning
        
        # Show initial summary
        self.print_enhanced_summary()
        
        cycle_count = 0
        last_backup_time = time.time()
        
        while self.running:
            try:
                cycle_count += 1
                print(f"\n{'='*25} CYCLE {cycle_count} {'='*25}")
                
                # Reload usernames every cycle - but don't block
                previous_username_count = len(self.usernames)
                self.usernames = self.load_usernames()
                
                if not self.usernames:
                    print("⚠️  No usernames in usernames.txt - continuing without bio/prompt updates")
                    self.usernames = []  # Empty list to prevent errors
                elif len(self.usernames) != previous_username_count:
                    print(f"📝 Username list updated: {previous_username_count} → {len(self.usernames)} usernames")
                
                # Check if we should process based on swipe time
                if not self.should_process_accounts_now():
                    current_hour = datetime.now().hour
                    start_hour, end_hour = map(int, self.config['swipe_time'].split('-'))
                    
                    # Calculate next swipe time
                    if current_hour < start_hour:
                        hours_until_swipe = start_hour - current_hour
                    elif current_hour > end_hour:
                        hours_until_swipe = (24 - current_hour) + start_hour
                    else:
                        hours_until_swipe = 0
                    
                    print(f"⏰ Outside swipe time ({self.config['swipe_time']})")
                    print(f"   Current hour: {current_hour}:00")
                    print(f"   Next swipe window in: {hours_until_swipe} hours")
                    print(f"   Checking again in 15 minutes...")
                    time.sleep(900)  # 15 minutes
                    continue
                
                # Always show current account status at start of each cycle
                self.print_enhanced_summary()
                
                # Get initial stats
                initial_total_likes, initial_likes_today = self.get_database_stats()
                
                # Backup database periodically
                if time.time() - last_backup_time > self.config['database_backup_interval']:
                    self.backup_database()
                    last_backup_time = time.time()
                
                # Import new tokens
                imported = self.import_tokens()
                if imported > 0:
                    print(f"✅ Imported {imported} new accounts")
                    self.print_enhanced_summary()
                
                # Get ready accounts
                ready_accounts = self.get_ready_accounts()
                
                if not ready_accounts:
                    print("📋 No accounts ready for processing")
                    
                    # Get all accounts to show why
                    all_accounts = self._get_all_accounts_for_status()
                    if all_accounts:
                        print("\n❓ Why no accounts were processed:")
                        self._print_detailed_account_status_with_timezone(all_accounts)
                    else:
                        print("   - No active accounts in database")
                        print("   - Import tokens by adding them to tokens.txt")
                        
                else:
                    print(f"🎯 Processing {len(ready_accounts)} accounts")
                    
                    # Process accounts with NO COOLDOWN between accounts
                    for i, account in enumerate(ready_accounts, 1):
                        if not self.running:
                            break
                        
                        print(f"\n{'─' * 50}")
                        print(f"📱 Account {i}/{len(ready_accounts)}")
                        print(f"{'─' * 50}")
                        
                        try:
                            self.process_single_account_enhanced(account)
                            # NO DELAY between accounts for faster processing
                            
                        except Exception as e:
                            print(f"❌ Processing error: {e}")
                            logging.error(f"Account processing error: {e}")
                            logging.error(traceback.format_exc())
                            
                            # Enhanced error recovery
                            self.adaptive_delay('long', "error recovery", 2.0)
                
                # Get final stats
                final_total_likes, final_likes_today = self.get_database_stats()
                
                # Cycle summary
                likes_gained = final_total_likes - initial_total_likes
                if likes_gained > 0:
                    print(f"\n✅ Cycle {cycle_count} complete: +{likes_gained} likes")
                else:
                    print(f"\n✅ Cycle {cycle_count} complete")

                # Print detailed account summary before waiting
                print("\n" + "="*70)
                print("📊 CURRENT ACCOUNT OVERVIEW")
                print("="*70)
                self.print_enhanced_summary()
                
                # Show next check times for accounts
                self._print_next_check_times()

                # Wait between cycles
                wait_time = self.config.get('wait_between_cycles', 900)  # Default 15 minutes
                wait_minutes = wait_time // 60
                wait_seconds = wait_time % 60
                
                if wait_seconds > 0:
                    print(f"\n⏱️  Waiting {wait_minutes} minutes {wait_seconds} seconds before next cycle...")
                else:
                    print(f"\n⏱️  Waiting {wait_minutes} minutes before next cycle...")
                print("    Press Ctrl+C to stop")
                print("="*70)
                
                # Sleep with interrupt handling
                try:
                    time.sleep(wait_time)
                except KeyboardInterrupt:
                    print("\n🛑 Interrupted during wait")
                    break
                
            except KeyboardInterrupt:
                print("\n🛑 Bot stopped by user")
                break
            except Exception as e:
                print(f"\n❌ Critical error in main loop: {e}")
                logging.error(f"Critical error: {e}")
                logging.error(traceback.format_exc())
                
                if self.config['auto_restart_on_error']:
                    error_delay = self.config['error_retry_delay']
                    print(f"⏱️  Auto-restart in {error_delay} seconds...")
                    try:
                        time.sleep(error_delay)
                    except KeyboardInterrupt:
                        print("\n🛑 Auto-restart cancelled")
                        break
                else:
                    print("🛑 Stopping due to critical error")
                    break
        
        # Final stats
        try:
            final_total_likes, final_likes_today = self.get_database_stats()
        except:
            final_total_likes = 0
            final_likes_today = 0
        
        print("\n" + "="*50)
        print("👋 TinderBot shutdown complete")
        print(f"📊 Final stats: {final_total_likes} total likes, {final_likes_today} today")
        print("="*50)

    def _parse_time_range(self, time_range_str: str) -> Tuple[int, int]:
        """Parse time range string, ignoring comments and extra spaces"""
        # Remove comments (anything after '#') and strip whitespace
        clean_str = time_range_str.split('#')[0].strip()
        
        if not clean_str:
            return (16, 18)  # Default value
        
        parts = clean_str.split('-')
        if len(parts) < 2:
            return (16, 18)  # Default format
        
        try:
            start = int(parts[0].strip())
            end = int(parts[1].strip())
            return (start, end)
        except (ValueError, TypeError):
            return (16, 18)  # Fallback to default

    def _print_next_check_times(self):
        """Print when each account will next check for likes"""
        try:
            time_range = self.config.get('swipe_time', '0-23')  # Changed from get_like_count_time
            print(f"\n⏰ Next Like Check Times (during swipe time {time_range}):")
            start_hour, end_hour = self._parse_time_range(time_range)

            
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT a.id, a.assigned_city, a.timezone_name, s.liked_me_count, 
                        s.last_liked_me_check
                    FROM accounts a
                    LEFT JOIN account_status s ON a.id = s.account_id
                    WHERE a.status = 'active'
                    ORDER BY a.assigned_city
                """)
                
                accounts = cursor.fetchall()
                
                if accounts:
                    print(f"\n⏰ Next Like Check Times (during {time_range} window):")
                    for account in accounts:
                        account_id, city, timezone_name, liked_count, last_check = account
                        
                        if not city:
                            city = "Unknown"
                        if not timezone_name:
                            timezone_name = "UTC"
                        
                        try:
                            tz = pytz.timezone(timezone_name)
                            local_time = datetime.now(tz)
                            
                            # If has likes, no need to check
                            if liked_count and liked_count > 0:
                                print(f"   • {city}: Has {liked_count} likes to process")
                            else:
                                # Calculate next check time within the window
                                if last_check:
                                    if isinstance(last_check, str):
                                        last_check = datetime.fromisoformat(last_check)
                                    if last_check.tzinfo is None:
                                        last_check = pytz.UTC.localize(last_check)
                                    last_check_local = last_check.astimezone(tz)
                                    
                                    # If checked today, next check is tomorrow
                                    if last_check_local.date() == local_time.date():
                                        next_check = local_time.replace(hour=start_hour, minute=0, second=0) + timedelta(days=1)
                                        hours_until = (next_check - local_time).total_seconds() / 3600
                                        print(f"   • {city}: Tomorrow at {start_hour}:00-{end_hour}:00 ({hours_until:.1f} hours)")
                                    else:
                                        # Check today if in window
                                        if local_time.hour < start_hour:
                                            next_check = local_time.replace(hour=start_hour, minute=0, second=0)
                                            hours_until = (next_check - local_time).total_seconds() / 3600
                                            print(f"   • {city}: Today at {start_hour}:00-{end_hour}:00 ({hours_until:.1f} hours)")
                                        elif local_time.hour <= end_hour:
                                            print(f"   • {city}: Can check now! (within {time_range} window)")
                                        else:
                                            next_check = local_time.replace(hour=start_hour, minute=0, second=0) + timedelta(days=1)
                                            hours_until = (next_check - local_time).total_seconds() / 3600
                                            print(f"   • {city}: Tomorrow at {start_hour}:00-{end_hour}:00 ({hours_until:.1f} hours)")
                                else:
                                    # Never checked
                                    if local_time.hour < start_hour:
                                        print(f"   • {city}: Today at {start_hour}:00-{end_hour}:00 (first check)")
                                    elif local_time.hour <= end_hour:
                                        print(f"   • {city}: Can check now! (first check)")
                                    else:
                                        print(f"   • {city}: Tomorrow at {start_hour}:00-{end_hour}:00 (first check)")
                        except Exception as e:
                            print(f"   • {city}: Error calculating time")
                            
        except Exception as e:
            logging.error(f"Error printing next check times: {e}")
    
    
    def _get_all_accounts_for_status(self) -> List[Dict]:
            """Get all active accounts for status display"""
            try:
                with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT a.*, s.* FROM accounts a
                        LEFT JOIN account_status s ON a.id = s.account_id
                        WHERE a.status = 'active'
                    """)
                    
                    accounts = []
                    for row in cursor.fetchall():
                        account = dict(zip([col[0] for col in cursor.description], row))
                        accounts.append(account)
                    
                    return accounts
            except Exception as e:
                logging.error(f"Error getting accounts for status: {e}")
                return []
    
    
    
    def print_enhanced_summary(self):
            """Print clean account summary that always stays visible"""
            try:
                with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                    cursor = conn.cursor()
                    
                    # Get account counts by status
                    cursor.execute("""
                        SELECT 
                            status,
                            COUNT(*) as count
                        FROM accounts 
                        GROUP BY status
                    """)
                    status_stats = cursor.fetchall()
                    
                    # Get active accounts with Gold status
                    cursor.execute("""
                        SELECT 
                            a.id,
                            a.assigned_city,
                            a.assigned_username,
                            s.is_gold,
                            s.gold_expires_at,
                            s.liked_me_count,
                            s.last_session_end,
                            a.status
                        FROM accounts a
                        LEFT JOIN account_status s ON a.id = s.account_id
                        WHERE a.status = 'active'
                        ORDER BY a.assigned_city
                    """)
                    active_accounts = cursor.fetchall()
                    
                    # Get today's statistics
                    cursor.execute("""
                        SELECT COUNT(*) FROM enhanced_activity 
                        WHERE activity_type = 'like' AND success = 1 
                        AND date(timestamp) = date('now')
                    """)
                    likes_today = cursor.fetchone()[0] or 0
                    
                    cursor.execute("""
                        SELECT SUM(matches_gained) FROM enhanced_sessions 
                        WHERE date(session_start) = date('now')
                    """)
                    matches_today = cursor.fetchone()[0] or 0
                    
                    # Get total statistics
                    cursor.execute("""
                        SELECT COUNT(*) FROM enhanced_activity 
                        WHERE activity_type = 'like' AND success = 1
                    """)
                    total_likes = cursor.fetchone()[0] or 0
                    
                    cursor.execute("""
                        SELECT SUM(matches_gained) FROM enhanced_sessions
                    """)
                    total_matches = cursor.fetchone()[0] or 0
                    
                    print("\n" + "=" * 70)
                    print("📊 ACCOUNT STATUS")
                    print("=" * 70)
                    
                    # Show account counts by status
                    for status, count in status_stats:
                        status_emoji = {
                            'active': '✅',
                            'banned': '🚫',
                            'dead': '💀',
                            'error': '⚠️'
                        }.get(status, '❓')
                        print(f"{status_emoji} {status.title()}: {count}")
                    
                    print("-" * 70)
                    
                    # Show active accounts with Gold/Free status
                    if active_accounts:
                        print("📋 Active Accounts:")
                        gold_count = 0
                        free_count = 0
                        
                        for account in active_accounts:
                            (account_id, city, username, is_gold, gold_expires_at, 
                            liked_me_count, last_session_end, status) = account
                            
                            city = city or "Unknown"
                            username = username or "Unknown"
                            liked_me_count = liked_me_count or 0
                            
                            # Determine Gold/Free status
                            if is_gold:
                                gold_count += 1
                                if gold_expires_at:
                                    if isinstance(gold_expires_at, str):
                                        expires = gold_expires_at[:10]
                                    else:
                                        expires = gold_expires_at.strftime('%Y-%m-%d')
                                    status_text = f"💛 GOLD (expires {expires})"
                                else:
                                    status_text = "💛 GOLD"
                            else:
                                free_count += 1
                                status_text = "🆓 FREE"
                            
                            # Format last session time
                            if last_session_end:
                                if isinstance(last_session_end, str):
                                    last_session = last_session_end.split('.')[0]
                                else:
                                    last_session = last_session_end.strftime('%Y-%m-%d %H:%M')
                            else:
                                last_session = "Never"
                            
                            print(f"   • {city} ({username}) - {status_text} - 💕 {liked_me_count} - Last: {last_session}")
                        
                        print(f"\n   Summary: {gold_count} Gold, {free_count} Free accounts")
                    else:
                        print("   No active accounts")
                    
                    print("-" * 70)
                    print(f"📅 Today: {likes_today} likes, {matches_today} matches")
                    print(f"📈 Total: {total_likes} likes, {total_matches} matches")
                    print("=" * 70)
                    
            except Exception as e:
                print(f"❌ Error generating summary: {e}")
                logging.error(f"Error generating summary: {e}")    
    def _print_no_accounts_reasons(self):
        """Print detailed reasons why no accounts are ready"""
        print("   Possible reasons:")
        print("   - No accounts imported")
        print("   - All accounts hit daily limits")
        print("   - Outside swipe time window")
        print("   - Accounts in session cooldown")
        print("   - High ban scores detected")
        print("   - Too many consecutive errors")
        print("   - Accounts flagged by enhanced detection")
    
    def backup_database(self):
        """Enhanced database backup with compression"""
        try:
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f"enhanced_tinder_bot_backup_{timestamp}.db"
            
            import shutil
            shutil.copy2("tinder_bot.db", backup_file)
            
            # Keep only last 15 backups (increased for enhanced version)
            backups = sorted(backup_dir.glob("*.db"), key=lambda x: x.stat().st_mtime)
            if len(backups) > 15:
                for old_backup in backups[:-15]:
                    old_backup.unlink()
            
          #  logging.info(f"Enhanced database backed up to {backup_file}")
            
        except Exception as e:
            logging.error(f"Error backing up enhanced database: {e}")
    




    def import_tokens(self) -> int:
        """Import tokens with enhanced validation and support for simplified format"""
        if not os.path.exists('tokens.txt'):
            return 0
        
        imported_count = 0
        failed_tokens = []
        
        # Try different encodings
        content = None
        
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                with open('tokens.txt', 'r', encoding=encoding) as f:
                    lines = f.readlines()
                content = lines
                break
            except Exception as e:
                continue
        
        if not content:
            return 0
        
        try:
            for i, line in enumerate(content, 1):
                line = line.strip()
                
                # Remove BOM and problematic characters
                line = line.replace('\ufeff', '').replace('\x00', '')
                
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(':')
                
                if len(parts) < 3:
                    failed_tokens.append(line)
                    continue
                
                try:
                    # Check if this looks like the simplified format: auth:persistent:refresh:lat:lon:proxy_parts
                    # We can identify this if parts[0] looks like a UUID and parts[3] looks like latitude
                    is_simplified_format = False
                    if len(parts) >= 5:
                        try:
                            # Try to parse the 4th part as a latitude
                            lat_test = float(parts[3])
                            if -90 <= lat_test <= 90:
                                is_simplified_format = True
                        except ValueError:
                            is_simplified_format = False
                    
                    if is_simplified_format and len(parts) >= 5:
                        # SIMPLIFIED FORMAT: auth:persistentID:refresh:lat:long:proxy_parts...
                        auth_token = parts[0].strip()           # d229ef2e-bad2-4270-a1e4-2dbd954a12b2
                        persistent_device_id = parts[1].strip() # a560c124945a07ef  
                        refresh_token = parts[2].strip()        # eyJhbGciOiJIUzI1NiJ9...
                        
                        # Parse coordinates safely
                        try:
                            latitude = float(parts[3].strip()) if parts[3].strip() and parts[3].strip() != '0' else None    # 19.076090
                            longitude = float(parts[4].strip()) if parts[4].strip() and parts[4].strip() != '0' else None   # 72.877426
                        except (ValueError, IndexError):
                            latitude = None
                            longitude = None
                        
                        # Handle proxy - could be split across multiple parts due to colons
                        if len(parts) > 5:
                            proxy_parts = parts[5:]
                            proxy_combined = ':'.join(proxy_parts).strip()
                            proxy = proxy_combined if proxy_combined else None
                        else:
                            proxy = None
                        
                        # Generate missing IDs randomly
                        device_id = persistent_device_id  # Use persistent ID as device ID (a560c124945a07ef)
                        install_id = self._generate_install_id()
                        appsflyer_id = self._generate_appsflyer_id()
                        advertising_id = self._generate_advertising_id()
                        device_ram = self._generate_device_ram()
                        os_version = self._generate_os_version()
                        
                    elif len(parts) >= 11:
                        # FULL FORMAT: auth:refresh:device:persistent:install:appsflyer:advertising:ram:os:lon:lat:proxy
                        auth_token = parts[0].strip()
                        refresh_token = parts[1].strip()
                        device_id = parts[2].strip()
                        persistent_device_id = parts[3].strip()
                        install_id = parts[4].strip()
                        appsflyer_id = parts[5].strip()
                        advertising_id = parts[6].strip()
                        device_ram = parts[7].strip()
                        os_version = parts[8].strip()
                        longitude = float(parts[9].strip()) if parts[9].strip() else None
                        latitude = float(parts[10].strip()) if parts[10].strip() else None
                        proxy = parts[11].strip() if len(parts) > 11 else None
                        
                    elif len(parts) >= 9:
                        # ENHANCED FORMAT: auth:refresh:device:persistent:install:appsflyer:advertising:ram:os:proxy
                        auth_token = parts[0].strip()
                        refresh_token = parts[1].strip()
                        device_id = parts[2].strip()
                        persistent_device_id = parts[3].strip()
                        install_id = parts[4].strip()
                        appsflyer_id = parts[5].strip()
                        advertising_id = parts[6].strip()
                        device_ram = parts[7].strip()
                        os_version = parts[8].strip()
                        longitude = None
                        latitude = None
                        proxy = parts[9].strip() if len(parts) > 9 else None
                        
                    else:
                        # LEGACY FORMAT: auth:refresh:device:proxy
                        auth_token = parts[0].strip()
                        refresh_token = parts[1].strip()
                        device_id = parts[2].strip()
                        persistent_device_id = device_id
                        install_id = self._generate_install_id()
                        appsflyer_id = self._generate_appsflyer_id()
                        advertising_id = self._generate_advertising_id()
                        device_ram = self._generate_device_ram()
                        os_version = self._generate_os_version()
                        longitude = None
                        latitude = None
                        proxy = parts[3].strip() if len(parts) > 3 else None
                        
                    # Enhanced validation
                    if not self._validate_token_format(auth_token, refresh_token, device_id):
                        failed_tokens.append(line)
                        continue
                    
                    # IMPORTANT: Pass parameters in the correct order
                    if self.process_single_token_enhanced(
                        auth_token, refresh_token, device_id, persistent_device_id,
                        install_id, appsflyer_id, advertising_id, device_ram, os_version,
                        longitude, latitude, proxy
                    ):
                        imported_count += 1
                    else:
                        failed_tokens.append(line)
                    
                    # Enhanced delay between imports
                    self.adaptive_delay('medium', "between token imports")
                    
                except Exception as e:
                    failed_tokens.append(line)
                    logging.error(f"Error processing token: {e}")
            
            # Update tokens.txt with enhanced format
            if failed_tokens:
                with open('tokens.txt', 'w', encoding='utf-8') as f:
                    f.write("# Failed tokens - please check format\n")
                    f.write("# Supported formats:\n")
                    f.write("# Simplified: auth_token:persistent_device_id:refresh_token:lat:lon:proxy\n")
                    f.write("# Enhanced: auth_token:refresh_token:device_id:persistent_device_id:install_id:appsflyer_id:advertising_id:device_ram:os_version:long:lat:proxy\n")
                    for failed_token in failed_tokens:
                        #f.write(failed_token + '\n')
                        pass
            else:
                with open('tokens.txt', 'w', encoding='utf-8') as f:
                    f.write("# All tokens imported successfully with enhanced processing\n")
            
        except Exception as e:
            logging.error(f"Error in enhanced token import: {e}")
        
        return imported_count



    def _validate_token_format(self, auth_token: str, refresh_token: str, device_id: str) -> bool:
        """Enhanced token format validation"""
        if not auth_token or len(auth_token) < 10:
            print(f"   ❌ Invalid auth token format")
            return False
        
        if not refresh_token or len(refresh_token) < 10:
            print(f"   ❌ Invalid refresh token format")
            return False
        
        if not device_id or len(device_id) < 8:
            print(f"   ❌ Invalid device ID format")
            return False
        
        # Check for common token patterns
        if not any(c.isalnum() for c in auth_token):
            print(f"   ❌ Auth token contains no alphanumeric characters")
            return False
        
        return True
   
   
            
        
    
   
   
   
    def create_account_record_enhanced(self, auth_token: str, refresh_token: str, device_id: str,
                                     persistent_device_id: str, install_id: str, appsflyer_id: str,
                                     advertising_id: str, device_ram: str, os_version: str, proxy: Optional[str],
                                     user_id: Optional[str], assigned_city: Optional[str],
                                     assigned_username: Optional[str], coordinates: Optional[Tuple],
                                     is_gold: bool, liked_me_count: int, gold_expires_at: Optional[str],
                                     ban_score: float) -> Optional[int]:
        """Create enhanced account record with additional tracking"""
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                
                # Get timezone for location
                timezone_name = self.get_timezone_for_coordinates(coordinates) if coordinates else "UTC"
                
                # Insert enhanced account
                cursor.execute("""
                    INSERT INTO accounts 
                    (auth_token, refresh_token, device_id, persistent_device_id, install_id,
                    appsflyer_id, advertising_id, device_ram, os_version, proxy, user_id, assigned_city,
                    assigned_username, coordinates_lat, coordinates_lon, timezone_name, ban_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    auth_token, refresh_token, device_id, persistent_device_id, install_id,
                    appsflyer_id, advertising_id, device_ram, os_version, proxy, user_id, assigned_city,
                    assigned_username,
                    coordinates[0] if coordinates else None,
                    coordinates[1] if coordinates else None,
                    timezone_name, ban_score
                ))
                
                account_id = cursor.lastrowid
                
                # Convert gold_expires_at
                gold_expires_datetime = None
                if gold_expires_at:
                    try:
                        gold_expires_datetime = datetime.fromisoformat(gold_expires_at)
                    except:
                        gold_expires_datetime = None
                
                # Insert enhanced account status
                cursor.execute("""
                    INSERT INTO account_status 
                    (account_id, is_gold, gold_expires_at, liked_me_count, current_session_phase)
                    VALUES (?, ?, ?, ?, ?)
                """, (account_id, is_gold, gold_expires_datetime, liked_me_count, 'startup'))
                
                conn.commit()
                return account_id
                
        except Exception as e:
            logging.error(f"Error creating enhanced account record: {e}")
            return None
    
    def assign_username_enhanced(self, city: str) -> Optional[str]:
        """Enhanced username assignment - return None if no usernames available"""
        if not self.usernames:
            return None  # Return None instead of trying to pick from empty list
        
        if not city:
            return random.choice(self.usernames) if self.usernames else None
        
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                
                # Create username_usage table if it doesn't exist
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS username_usage (
                        username TEXT,
                        city TEXT,
                        used_count INTEGER DEFAULT 0,
                        last_used TIMESTAMP,
                        PRIMARY KEY (username, city)
                    )
                """)
                
                # Shuffle for variety
                shuffled_usernames = self.usernames.copy()
                random.shuffle(shuffled_usernames)
                
                for username in shuffled_usernames:
                    cursor.execute("""
                        SELECT used_count FROM username_usage 
                        WHERE username = ? AND city = ?
                    """, (username, city))
                    
                    result = cursor.fetchone()
                    used_count = result[0] if result else 0
                    
                    if used_count < self.config['tinders_per_username']:
                        # Update usage with enhanced tracking
                        cursor.execute("""
                            INSERT OR REPLACE INTO username_usage 
                            (username, city, used_count, last_used)
                            VALUES (?, ?, ?, ?)
                        """, (username, city, used_count + 1, datetime.now()))
                        
                        conn.commit()
                        logging.info(f"Enhanced username assignment: {username} for {city}")
                        return username
                
                # If all usernames are exhausted, return random one
                selected = random.choice(self.usernames)
                logging.warning(f"All usernames exhausted for {city}, using {selected}")
                return selected
                
        except Exception as e:
            logging.error(f"Error in enhanced username assignment: {e}")
            return random.choice(self.usernames) if self.usernames else None
   
   
   
   
   
    def get_timezone_for_coordinates(self, coordinates: Tuple[float, float]) -> str:
        """Enhanced timezone detection with more accurate mapping"""
        lat, lon = coordinates
        
        # Enhanced timezone mapping with more precision
        if -180 <= lon < -165: return "Pacific/Honolulu"
        elif -165 <= lon < -150: return "US/Alaska"
        elif -150 <= lon < -135: return "US/Alaska"
        elif -135 <= lon < -120: return "US/Pacific"
        elif -120 <= lon < -105: return "US/Mountain"
        elif -105 <= lon < -90: return "US/Central"
        elif -90 <= lon < -75: return "US/Eastern"
        elif -75 <= lon < -45: return "America/Sao_Paulo"
        elif -45 <= lon < -15: return "Atlantic/Azores"
        elif -15 <= lon < 15: return "Europe/London"
        elif 15 <= lon < 30: return "Europe/Berlin"
        elif 30 <= lon < 45: return "Europe/Moscow"
        elif 45 <= lon < 75: return "Asia/Dubai"
        elif 75 <= lon < 105: return "Asia/Kolkata"
        elif 105 <= lon < 120: return "Asia/Shanghai"
        elif 120 <= lon < 135: return "Asia/Tokyo"
        elif 135 <= lon < 150: return "Australia/Sydney"
        elif 150 <= lon <= 180: return "Pacific/Auckland"
        else: return "UTC"
    
    def get_city_for_coordinates(self, lat: float, lon: float) -> Optional[str]:
        """Enhanced city detection with better accuracy"""
        try:
            min_distance = float('inf')
            closest_city = None
            
            for city_info in self.cities:
                # Calculate approximate distance using Haversine formula
                city_lat, city_lon = city_info['lat'], city_info['lon']
                
                # Simple distance calculation (good enough for city matching)
                lat_diff = abs(lat - city_lat)
                lon_diff = abs(lon - city_lon)
                distance = (lat_diff ** 2 + lon_diff ** 2) ** 0.5
                
                if distance < min_distance and distance < 0.5:  # Within ~55km
                    min_distance = distance
                    closest_city = f"{city_info['city']}, {city_info['country']}"
            
            return closest_city
            
        except Exception as e:
            logging.error(f"Error getting city for coordinates: {e}")
            return None
    
    def check_gold_status(self, profile_data: Dict) -> Tuple[bool, Optional[str]]:
        """Enhanced Gold subscription status check"""
        try:
            purchases = profile_data.get("data", {}).get("purchase", {}).get("purchases", [])
            
            for purchase in purchases:
                if (purchase.get("product_type") in ["gold", "plus"] and 
                    purchase.get("payment_pending", False) == False):
                    
                    expire_date = purchase.get("expire_date")
                    if expire_date:
                        try:
                            if isinstance(expire_date, int):
                                if expire_date > 10**12:
                                    expire_datetime = datetime.fromtimestamp(expire_date / 1000)
                                else:
                                    expire_datetime = datetime.fromtimestamp(expire_date)
                            else:
                                expire_datetime = datetime.fromisoformat(expire_date)
                            
                            if expire_datetime > datetime.now():
                                return True, expire_datetime.isoformat()
                        except Exception as e:
                            logging.warning(f"Error parsing expiry date: {e}")
            
            return False, None
            
        except Exception as e:
            logging.error(f"Error checking enhanced Gold status: {e}")
            return False, None




    def should_check_likes_for_account(self, account: Dict) -> bool:
        """Check if we should check likes based on account's local timezone and swipe time"""
        account_id = account['id']
        timezone_name = account.get('timezone_name', 'UTC')
        
        try:
            # Use SwipeTime from config instead of separate GetLikeCountTime
            time_range = self.config.get('swipe_time', '8-22')
            start_hour, end_hour = map(int, time_range.split('-'))
            
            # Get account's local time based on passport location
            tz = pytz.timezone(timezone_name)
            local_time = datetime.now(tz)
            current_hour = local_time.hour
            
            # Check if current hour is within the interval
            if start_hour <= end_hour:
                in_time_window = start_hour <= current_hour <= end_hour
            else:  # Handle cases like "22-2" (10 PM to 2 AM)
                in_time_window = current_hour >= start_hour or current_hour <= end_hour
            
            if not in_time_window:
                return False
            
            # Check if we already checked today
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT last_liked_me_check FROM account_status 
                    WHERE account_id = ?
                """, (account_id,))
                
                result = cursor.fetchone()
                if result and result[0]:
                    last_check = result[0]
                    if isinstance(last_check, str):
                        last_check = datetime.fromisoformat(last_check)
                    
                    # Convert to account's timezone
                    if last_check.tzinfo is None:
                        last_check = pytz.UTC.localize(last_check)
                    
                    last_check_local = last_check.astimezone(tz)
                    
                    # Check if we already checked today
                    if last_check_local.date() == local_time.date():
                        return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error checking if should check likes: {e}")
            return False
    
    
    
    def update_liked_me_check(self, account_id: int, liked_me_count: int):
        """Update the last liked_me check timestamp and count"""
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE account_status 
                    SET last_liked_me_check = ?, last_liked_me_check_count = ?, liked_me_count = ?
                    WHERE account_id = ?
                """, (datetime.now(), liked_me_count, liked_me_count, account_id))
                conn.commit()
        except Exception as e:
            logging.error(f"Error updating liked_me check: {e}")

    def check_and_update_likes_if_needed(self, api: TinderApi, account: Dict) -> Optional[int]:
        """Check likes only if conditions are met and no likes are already cached"""
        account_id = account['id']
        city = account.get('assigned_city', 'Unknown')
        timezone_name = account.get('timezone_name', 'UTC')
        
        # Use SwipeTime from config
        time_range = self.config.get('swipe_time', '8-22')
        
        # Get current liked_me count from database
        try:
            with sqlite3.connect("tinder_bot.db", detect_types=sqlite3.PARSE_DECLTYPES) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT liked_me_count, last_liked_me_check FROM account_status 
                    WHERE account_id = ?
                """, (account_id,))
                
                result = cursor.fetchone()
                cached_count = result[0] if result else 0
                last_check = result[1] if result else None
        except:
            cached_count = 0
            last_check = None
        
        # Get local time for account
        try:
            tz = pytz.timezone(timezone_name)
            local_time = datetime.now(tz)
            local_time_str = local_time.strftime('%H:%M')
        except:
            local_time_str = 'Unknown'
            tz = pytz.UTC
            local_time = datetime.now(tz)
        
        # If we already have likes, no need to check again
        if cached_count > 0:
            print(f"   💕 Using cached liked me count: {cached_count}")
            return cached_count
        
        # Check if it's time to check likes
        if self.should_check_likes_for_account(account):
            print(f"   🔍 Checking likes for {city} (Local time {local_time_str} is within swipe time {time_range})")
            
            # Make API call to get liked_me count
            liked_me_count = api.liked_me_count()
            
            if liked_me_count is not None:
                self.update_liked_me_check(account_id, liked_me_count)
                
                if liked_me_count > 0:
                    print(f"   💕 Liked me count: {liked_me_count} - Ready to process!")
                    return liked_me_count
                else:
                    print(f"   💔 No likes yet - will check again tomorrow during swipe time {time_range}")
                    return 0
            else:
                print(f"   ❌ Failed to get liked me count")
                return cached_count
        else:
            # Show why we're not checking
            if last_check:
                if isinstance(last_check, str):
                    last_check = datetime.fromisoformat(last_check)
                if last_check.tzinfo is None:
                    last_check = pytz.UTC.localize(last_check)
                last_check_local = last_check.astimezone(tz)
                
                if last_check_local.date() == local_time.date():
                    print(f"   ⏰ Already checked today at {last_check_local.strftime('%H:%M')} local time - Won't check again until tomorrow")
                else:
                    print(f"   ⏰ Waiting for swipe time {time_range} (currently {local_time_str} local time)")
            else:
                print(f"   ⏰ Waiting for swipe time {time_range} (currently {local_time_str} local time)")
            
            return 0

def main():
    """Enhanced main function with better argument handling"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "status":
            bot = EnhancedTinderBot()
            bot.print_enhanced_summary()
            return
        elif command == "import":
            bot = EnhancedTinderBot()
            imported = bot.import_tokens()
            print(f"Enhanced import complete: {imported} accounts imported")
            bot.print_enhanced_summary()
            return
        elif command == "help":
            print("🔥 Enhanced Anti-Detection Tinder Bot v2.0 Commands:")
            print("  python tinder_bot.py          - Run enhanced bot with triple patterns")
            print("  python tinder_bot.py status   - Show enhanced account analytics")
            print("  python tinder_bot.py import   - Import tokens with enhanced validation")
            print("  python tinder_bot.py help     - Show this help")
            return
    
    # Default: run the enhanced bot
    bot = EnhancedTinderBot()
    bot.run_enhanced()


if __name__ == "__main__":
    main()