#!/usr/bin/env python3
"""
Enhanced TinderApi - Complete Anti-Detection Version
Implements exact request patterns from HAR analysis to avoid bans
"""

import datetime
import requests
import requests_go 
from requests_go import tls_config , RequestException

import uuid
import time
import random
import json
from typing import Optional, Tuple, Dict, Any, List
import traceback
import logging
import os



def tls_settings():
    return  {
        "donate": "Please consider donating to keep this API running. Visit https://tls.peet.ws",
        "http_version": "h2",
        "method": "POST",  # Changed from GET to POST
        "user_agent": "Tinder Android Version 16.11.0",
        "tls": {
            "ciphers": [
            "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
            "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
            "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
            "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
            "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",
            "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA",
            "TLS_RSA_WITH_AES_128_GCM_SHA256",
            "TLS_RSA_WITH_AES_256_GCM_SHA384",
            "TLS_RSA_WITH_AES_128_CBC_SHA",
            "TLS_RSA_WITH_AES_256_CBC_SHA"
            ],
            "extensions": [
            {
                "name": "extensionRenegotiationInfo (boringssl) (65281)",
                "data": "00"
            },
            {
                "name": "server_name (0)",
                "server_name": "api.gotinder.com"  # Changed to correct domain
            },
            {
                "name": "extended_master_secret (23)",
                "master_secret_data": "",
                "extended_master_secret_data": ""
            },
            {
                "name": "session_ticket (35)",
                "data": ""
            },
            {
                "name": "signature_algorithms (13)",
                "signature_algorithms": [
                "ecdsa_secp256r1_sha256",
                "rsa_pss_rsae_sha256",
                "rsa_pkcs1_sha256",
                "ecdsa_secp384r1_sha384",
                "rsa_pss_rsae_sha384",
                "rsa_pkcs1_sha384",
                "rsa_pss_rsae_sha512",
                "rsa_pkcs1_sha512",
                "rsa_pkcs1_sha1"
                ]
            },
            {
                "name": "status_request (5)",
                "status_request": {
                "certificate_status_type": "OSCP (1)",
                "responder_id_list_length": 0,
                "request_extensions_length": 0
                }
            },
            {
                "name": "application_layer_protocol_negotiation (16)",
                "protocols": [
                "h2",
                "http/1.1"
                ]
            },
            {
                "name": "ec_point_formats (11)",
                "elliptic_curves_point_formats": [
                "0x00"
                ]
            },
            {
                "name": "supported_groups (10)",
                "supported_groups": [
                "X25519 (29)",
                "P-256 (23)",
                "P-384 (24)"
                ]
            }
            ],
            "tls_version_record": "771",
            "tls_version_negotiated": "771",
            "ja3": "771,49195-49196-52393-49199-49200-52392-49171-49172-156-157-47-53,65281-0-23-35-13-5-16-11-10,29-23-24,0",
            "ja3_hash": "6f5e62edfa5933b1332ddf8b9fb3ef9d",
            "ja4": "t12d129h2_d34a8e72043a_0154aa7a1cd1",
            "ja4_r": "t12d129h2_002f,0035,009c,009d,c013,c014,c02b,c02c,c02f,c030,cca8,cca9_0000,0005,000a,000b,000d,0017,0023,ff01_0403,0804,0401,0503,0805,0501,0806,0601,0201",
            "peetprint": "|2-1.1|29-23-24|1027-2052-1025-1283-2053-1281-2054-1537-513|0||49195-49196-52393-49199-49200-52392-49171-49172-156-157-47-53|0-10-11-13-16-23-35-5-65281",
            "peetprint_hash": "56b4a9c0c62272cd3a9257311697e41f",
            "client_random": "d133a5dc61496131dc0d16d338d40cbdbe15c075f8b86852bbcf4f4c6739bcae",
            "session_id": ""
        },
        "http2": {
            "akamai_fingerprint": "4:16777216|16711681|0|m,p,a,s",
            "akamai_fingerprint_hash": "605a1154008045d7e3cb3c6fb062c0ce",
            "sent_frames": [
            {
                "frame_type": "SETTINGS",
                "length": 6,
                "settings": [
                "INITIAL_WINDOW_SIZE = 16777216"
                ]
            },
            {
                "frame_type": "WINDOW_UPDATE",
                "length": 4,
                "increment": 16711681
            },
            {
                "frame_type": "HEADERS",
                "stream_id": 3,
                "length": 415,
                "headers": [
                ":method: POST",  # Changed to POST
                ":path: /v2/buckets",
                ":authority: api.gotinder.com",  # Changed to correct domain
                ":scheme: https",
                "x-auth-token: ",
                "user-agent: Tinder Android Version 16.11.0",
                "os-version: 28",
                "app-version: 4732",
                "platform: android",
                "platform-variant: Google-Play",
                "x-supported-image-formats: webp",
                "accept-language: en-US",
                "tinder-version: 16.11.0",
                "store-variant: Play-Store",
                "x-device-ram: ",
                "persistent-device-id: ",
                "app-session-id: 2d30418c-f292-4ee8-887c-819afd696db2",
                "app-session-time-elapsed: 2656.113",
                "user-session-id: 9489f8dd-9165-4fcb-803c-7e72904ecaef",
                "user-session-time-elapsed: 2656.112",
                "install-id: dyVXuPN8wUI",
                "accept-encoding: gzip"
                ],
                "flags": [
                "EndStream (0x1)",
                "EndHeaders (0x4)"
                ]
            }
            ]
        },
        "tcpip": {
            "ip": {},
            "tcp": {}
        }
    }



class TinderApi:
    """Fixed TinderApi with proper request patterns"""
    
    def __init__(self, auth_token: str, refresh_token: str, persistent_device_id: str,
                 device_ram: str, os_version: str, install_id: str, appsflyer_id: Optional[str] = None,
                 advertising_id: Optional[str] = None, longitude: Optional[float] = None, 
                 latitude: Optional[float] = None, proxy: Optional[str] = None):
        # Core authentication
        self.auth_token = auth_token
        self.refresh_token = refresh_token
        self.persistent_device_id = persistent_device_id
        self.device_id = persistent_device_id  # For compatibility
        self.device_ram = device_ram or "5"  # Fix empty device_ram
        self.os_version = os_version or "34"  # Fix empty os_version
        self.install_id = install_id
         
        # Default coordinates from HAR (Mumbai, India)
        self.longitude = longitude or 72.83232585334929
        self.latitude = latitude or 18.95816587585886
        
        # IDs - use provided or generate
        self.appsflyer_id = appsflyer_id or f"{int(time.time() * 1000)}-{random.randint(1000000000000000000, 9999999999999999999)}"
        self.advertising_id = advertising_id or str(uuid.uuid4())
        
        # Session management (exact patterns from HAR)
        self.app_session_id = str(uuid.uuid4())
        self.user_session_id = str(uuid.uuid4())
        self.hubble_network_id = str(uuid.uuid4())
        self.funnel_session_id = str(uuid.uuid4())
        self.session_start_time = time.time()
        self.last_activity_date = None
        
        # Cache for If-Modified-Since headers
        self.last_modified_cache = {}
        
        # Request IDs for tracking
        self.x_request_id = str(uuid.uuid4())
        self.x_hubble_entity_id = str(uuid.uuid4())
        
        # Cache and proxy
        self.profile_cache = None
        self.profile_cache_time = 0
        self.profile_cache_ttl = 300  # 5 minutes
        self.proxies = {"socks5": proxy} if proxy else {}
        
        # Request tracking for anti-ban
        self.last_request_time = 0
        self.min_request_interval = 0.1
        
        # Error tracking
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
        logging.info(f"Enhanced TinderApi initialized for device {persistent_device_id[:8]}...")
    
    def _get_session_elapsed_time(self) -> float:
        """Get elapsed time since session start"""
        return round(time.time() - self.session_start_time, 3)
    
    def _generate_correlation_id(self) -> str:
        """Generate unique correlation ID"""
        return str(uuid.uuid4())
    
    def _enforce_rate_limit(self):
        """Enforce minimum time between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def headers(self, endpoint_type: str = "default", include_correlation: bool = True) -> Dict[str, str]:
        """Generate headers matching exact HAR patterns - FIXED VERSION"""
        elapsed_time = self._get_session_elapsed_time()
        
        # Base headers that appear in ALL requests (EXACT CASE FROM HAR)
        base_headers = {
            "User-Agent": "Tinder Android Version 16.11.0",  # Fixed capitalization
            "os-version": self.os_version,
            "app-version": "4732",
            "platform": "android",
            "platform-variant": "Google-Play",
            "x-supported-image-formats": "webp",
            "accept-language": "en-US",
            "tinder-version": "16.11.0",
            "store-variant": "Play-Store",
            "x-device-ram": self.device_ram,
            "persistent-device-id": self.persistent_device_id,
            "app-session-id": self.app_session_id,
            "app-session-time-elapsed": str(elapsed_time),
            "install-id": self.install_id,
            "accept-encoding": "gzip"
        }
        
        # Add auth token for authenticated requests
        if self.auth_token and endpoint_type not in ["auth", "healthcheck", "buckets_initial"]:
            base_headers["x-auth-token"] = self.auth_token
        
        # Add user session info for most requests
        if endpoint_type not in ["auth", "healthcheck", "buckets_initial"]:
            base_headers["user-session-id"] = self.user_session_id
            base_headers["user-session-time-elapsed"] = str(elapsed_time)
        
        # Add correlation ID for most requests
        if include_correlation and endpoint_type not in ["healthcheck", "auth"]:
            base_headers["x-correlation-id"] = self._generate_correlation_id()
        
        # Endpoint-specific headers
        if endpoint_type == "auth":
            base_headers.update({
                "appsflyer-id": self.appsflyer_id,
                "advertising-id": self.advertising_id,
                "funnel-session-id": self.funnel_session_id,
                "Content-Type": "application/x-protobuf"  # Fixed capitalization
            })
            # Remove auth headers for auth requests
            base_headers.pop("x-auth-token", None)
            base_headers.pop("user-session-id", None)
            base_headers.pop("user-session-time-elapsed", None)
            
        elif endpoint_type == "profile":
            base_headers["support-short-video"] = "1"
            
        elif endpoint_type == "recs":
            base_headers.update({
                "support-short-video": "1",
                "connection-speed": str(random.randint(50, 1000)),
                "x-request-id": self.x_request_id,
                "x-hubble-entity-id": self.x_hubble_entity_id
            })
            
        elif endpoint_type == "like":
            base_headers["x-hubble-network-id"] = self.hubble_network_id
            
        elif endpoint_type == "json_post":
            base_headers["Content-Type"] = "application/json; charset=UTF-8"
        
        # Remove debug print
        return base_headers
    
    
    
    def _make_request(self, method: str, url: str, headers: Optional[Dict] = None, **kwargs):
        """Make authenticated request with retry logic and exact HAR behavior"""
        self._enforce_rate_limit()
        
        max_retries = 3
        backoff_factor = 2
        
        for attempt in range(max_retries):
            try:
                current_headers = headers if headers else self.headers()
                
                # Add If-Modified-Since header for GET requests if cached
                if method.upper() == 'GET' and url in self.last_modified_cache:
                    current_headers['If-Modified-Since'] = self.last_modified_cache[url]
                
                # Timeout variation for realism
                timeout = random.randint(25, 35)
                
                logging.debug(f"Making {method} request to {url}")
                
                # Make request
                response = requests_go.request(
                    method=method,
                    url=url,
                    headers=current_headers,
                    proxies=self.proxies,
                    timeout=timeout,
                    tls_config=tls_config.to_tls_config(tls_settings()),
                    **kwargs
                )
                
                # ALWAYS store the last response status for bot detection
                self._last_response_status = response.status_code if response else None
                
                # Cache Last-Modified header
                if response.status_code == 200 and 'Last-Modified' in response.headers:
                    self.last_modified_cache[url] = response.headers['Last-Modified']
                
                # Handle different response codes
                if response.status_code == 200:
                    self.consecutive_errors = 0
                    return response
                elif response.status_code == 304:  # Not Modified
                    logging.debug("Got 304 Not Modified")
                    return response
                elif response.status_code == 400:
                    logging.warning(f"Bad Request (400): {response.text[:200]}")
                    return response  # Return for analysis
                elif response.status_code == 401:
                   # logging.warning(f"Auth expired (401), attempting refresh...")
                    pass
                    # DON'T auto-refresh, let the bot handle it
                    return None
                elif response.status_code == 403:
                    logging.error("Account banned or access forbidden (403)")
                    # DON'T auto-refresh, let the bot handle it
                    return None
                elif response.status_code == 429:
                    # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logging.warning(f"Rate limited (429), waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                elif response.status_code >= 500:
                    # Server error, retry with backoff
                    logging.warning(f"Server error {response.status_code}, retrying...")
                    if attempt < max_retries - 1:
                        time.sleep(backoff_factor ** attempt)
                        continue
                else:
                    logging.warning(f"Request failed: {response.status_code}")
                    logging.debug(f"Response body: {response.text[:500]}")
                    return response
                    
            except requests.exceptions.Timeout:
                logging.error(f"Request timeout (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(backoff_factor ** attempt)
                    continue
            except Exception as e:
                logging.error(f"Request exception: {e}")
                logging.debug(traceback.format_exc())
                self.consecutive_errors += 1
                
                if self.consecutive_errors >= self.max_consecutive_errors:
                    logging.error(f"Too many consecutive errors ({self.consecutive_errors})")
                    self._last_response_status = None
                    return None
                
                if attempt < max_retries - 1:
                    time.sleep(backoff_factor ** attempt)
                    continue
        
        # Set status to None if we completely failed
        self._last_response_status = None
        return None
    
    # CORE APP LIFECYCLE METHODS (following exact HAR patterns)
    
    def healthcheck_auth(self) -> Optional[Dict]:
        """Health check for authentication status (exact HAR pattern)"""
        url = "https://api.gotinder.com/healthcheck/auth"
        headers = self.headers("healthcheck")
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return {"status": "not_modified"}
            try:
                return response.json()
            except:
                return {"status": "success"}
        return None
    
    def buckets(self) -> Optional[Dict]:
        """Get buckets (initial request for session establishment)"""
        url = "https://api.gotinder.com/v2/buckets"
        payload = {
            "device_id": self.install_id,
            "experiments": []
        }
        
        headers = self.headers("json_post")
        json_data = json.dumps(payload)
        headers["Content-Length"] = str(len(json_data.encode('utf-8')))
        
        response = self._make_request('POST', url, headers=headers, data=json_data)
        if response and response.status_code == 200:
            try:
                return response.json()
            except:
                return {"status": "success"}
        return None
    
    def device_check(self, is_background: bool = False) -> Optional[Dict]:
        """Device check for Android (exact HAR pattern)"""
        url = f"https://api.gotinder.com/v2/device-check/android?isBackground={str(is_background).lower()}"
        headers = self.headers()
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return {"status": "not_modified"}
            try:
                return response.json()
            except:
                return {"status": "success"}
        return None
    
    def send_profile_consents(self) -> bool:
        """Send profile consents (exact HAR payload)"""
        url = "https://api.gotinder.com/v2/profile/consents"
        
        # Exact payload from HAR analysis
        payload = {
            "categories": [
                {"code": "strictly_necessary", "default_value": True, "responded": True, "requires_input": False},
                {"code": "advertising", "default_value": True, "responded": True, "requires_input": False},
                {"code": "user_acquisition", "default_value": True, "responded": True, "requires_input": False},
                {"code": "mg_sharing", "default_value": True, "responded": True, "requires_input": False}
            ],
            "consents": [
                {"code": "adyen", "category_code": "strictly_necessary", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "bugsnag", "category_code": "strictly_necessary", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "facebook_auth", "category_code": "strictly_necessary", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "facetec", "category_code": "strictly_necessary", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "firebase_crashlytics", "category_code": "strictly_necessary", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "google_analytics_for_firebase", "category_code": "strictly_necessary", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "google_email_verification", "category_code": "strictly_necessary", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "netlify", "category_code": "strictly_necessary", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "opentok", "category_code": "strictly_necessary", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "spotify_auth", "category_code": "strictly_necessary", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "tinder_internal_analytics", "category_code": "strictly_necessary", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "criteo", "category_code": "advertising", "responded": True, "enabled": True, "requires_input": False, "version": "1"},
                {"code": "google_mobile_ads", "category_code": "advertising", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "marketcast", "category_code": "advertising", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "nimbus_ads", "category_code": "advertising", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "tinder_direct_sold_ads", "category_code": "advertising", "responded": True, "enabled": True, "requires_input": False, "version": "2"},
                {"code": "tinder_promotional_ads", "category_code": "advertising", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "unity_ads", "category_code": "advertising", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "video_amp", "category_code": "advertising", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "apps_flyer", "category_code": "user_acquisition", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "branch", "category_code": "user_acquisition", "responded": True, "enabled": True, "requires_input": False, "version": "0"},
                {"code": "mg_reporting", "category_code": "mg_sharing", "responded": True, "enabled": True, "requires_input": False, "version": "0"}
            ],
            "event_source": "post_auth",
            "tc_string": "",
            "tc_lever_enabled": False
        }
        
        headers = self.headers("json_post")
        json_payload = json.dumps(payload)
        headers["Content-Length"] = str(len(json_payload.encode('utf-8')))
        
        response = self._make_request('POST', url, headers=headers, data=json_payload)
        return response is not None and response.status_code == 200
    
    def get_updates(self, last_activity_date: Optional[str] = None, include_nudge: bool = False) -> Optional[Dict]:
        """Get updates with exact HAR pattern"""
        url = "https://api.gotinder.com/updates?is_boosting=false&boost_cursor=0"
        
        # Generate realistic last_activity_date if not provided
        if not last_activity_date:
            if self.last_activity_date:
                last_activity_date = self.last_activity_date
            else:
                # Use current time minus a few seconds
                last_activity_time = datetime.datetime.now() - datetime.timedelta(seconds=random.randint(5, 30))
                last_activity_date = last_activity_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-3] + "Z"
        
        payload = {"last_activity_date": last_activity_date}
        
        # Add nudge parameter if needed
        if include_nudge:
            payload["nudge"] = True
        
        headers = self.headers("json_post")
        json_payload = json.dumps(payload)
        headers["Content-Length"] = str(len(json_payload.encode('utf-8')))
        
        response = self._make_request('POST', url, headers=headers, data=json_payload)
        if response and response.status_code == 200:
            try:
                data = response.json()
                # Update cached activity date
                self.last_activity_date = last_activity_date
                return data
            except Exception as e:
                logging.error(f"Error parsing updates response: {e}")
                return {"status": "success"}
        return None
    
    def meta_post(self, lat: float, lon: float) -> Optional[Dict]:
        """Post meta information with location (exact HAR pattern)"""
        url = "https://api.gotinder.com/v2/meta"
        
        payload = {
            "lat": lat,
            "lon": lon,
            "force_fetch_resources": True
        }
        
        headers = self.headers("json_post")
        json_payload = json.dumps(payload)
        headers["Content-Length"] = str(len(json_payload.encode('utf-8')))
        
        response = self._make_request('POST', url, headers=headers, data=json_payload)
        if response and response.status_code == 200:
            try:
                return response.json()
            except:
                return {"status": "success"}
        return None
    
    def register_push_device(self, device_token: str) -> bool:
        """Register device for push notifications (exact HAR pattern)"""
        url = f"https://api.gotinder.com/v2/push/devices/android/{device_token}"
        
        payload = {
            "app_id": "com.tinder",
            "push_notification_version": 2,
            "push_settings": {}
        }
        
        headers = self.headers("json_post")
        json_payload = json.dumps(payload)
        headers["Content-Length"] = str(len(json_payload.encode('utf-8')))
        
        response = self._make_request('POST', url, headers=headers, data=json_payload)
        return response is not None and response.status_code == 200
    
    def update_user_language_preferences(self) -> bool:
        """Update user language preferences (exact HAR pattern)"""
        url = "https://api.gotinder.com/v2/profile/user"
        
        payload = {
            "global_mode": {
                "display_language": "en",
                "language_preferences": [
                    {"language": "en", "is_selected": True}
                ]
            }
        }
        
        headers = self.headers("json_post")
        json_payload = json.dumps(payload)
        headers["Content-Length"] = str(len(json_payload.encode('utf-8')))
        
        response = self._make_request('POST', url, headers=headers, data=json_payload)
        return response is not None and response.status_code == 200
    
    # PROFILE METHODS
    
    def profile(self, include_params: Optional[str] = None) -> Optional[Dict]:
        """Get user profile data with caching"""
        # Use cache if available and fresh
        if self.profile_cache and (time.time() - self.profile_cache_time) < self.profile_cache_ttl:
            logging.debug("Returning cached profile data")
            return self.profile_cache
        
        # Default comprehensive include parameters
        if not include_params:
            include_params = "offerings%2Cfeature_access%2Centrypoints%2Cswipenote%2Cpaywalls%2Cnudge_rules%2Cboost%2Ccompliance%2Caccount%2Cuser%2Cspotify%2Conboarding%2Cexplore_settings%2Clikes%2Ctravel%2Cmedia_tags%2Cavailable_descriptors%2Cprofile_meter%2Cphoto_prompts%2Ccampaigns%2Cemail_settings%2Ctop_photo%2Cpurchase%2Creadreceipts%2Csuper_likes%2Ctinder_u%2Ctutorials%2Conboarding%2Cplus_control"
        
        url = f"https://api.gotinder.com/v2/profile?include={include_params}"
        headers = self.headers("profile")
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code == 200:
            try:
                profile_data = response.json()
                self.profile_cache = profile_data
                self.profile_cache_time = time.time()
                return profile_data
            except Exception as e:
                logging.error(f"Error parsing profile response: {e}")
                return None
        return None
    
    def profileMeter(self) -> Optional[Dict]:
        """Get profile meter (exact HAR pattern)"""
        url = "https://api.gotinder.com/v2/profile?include=profile_meter"
        headers = self.headers("profile")
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return {"status": "not_modified"}
            try:
                return response.json()
            except Exception as e:
                logging.error(f"Error parsing profile meter response: {e}")
                return None
        return None
    
    def profileJob(self) -> Optional[Dict]:
        """Clear/update profile job information (exact HAR pattern)"""
        url = "https://api.gotinder.com/v2/profile/job"
        
        headers = self.headers("json_post")
        
        # Exact payload from HAR
        payload = {"jobs": [{"company": {"name": "", "displayed": False}, "title": {"name": "", "displayed": False}}]}
        json_data = json.dumps(payload)
        headers["Content-Length"] = str(len(json_data.encode('utf-8')))
        
        response = self._make_request('POST', url, headers=headers, data=json_data)
        if response and response.status_code == 200:
            try:
                return response.json()
            except Exception as e:
                logging.error(f"Error parsing profile job response: {e}")
                return None
        return None
    
    def update_bio(self, bio_text: str) -> Dict[str, Any]:
        """Update user bio (exact HAR pattern)"""
        url = "https://api.gotinder.com/v2/profile/user"
        
        payload = {"bio": bio_text}
        headers = self.headers("json_post")
        json_data = json.dumps(payload)
        headers["Content-Length"] = str(len(json_data.encode('utf-8')))
        
        response = self._make_request('POST', url, headers=headers, data=json_data)
        
        if response and response.status_code == 200:
            try:
                result = response.json()
                self.invalidate_profile_cache()
                logging.info("Bio updated successfully")
                return {"success": True, "changes_made": True, "response": result}
            except:
                return {"success": True, "changes_made": True}
        
        return {"success": False, "error": "API request failed"}
    
    def process_prompt(self, prompt_id: str, prompt_text: str) -> Dict[str, Any]:
        """Process prompts with exact HAR pattern"""
        try:
            # First clear job info (as seen in HAR)
            self.profileJob()
            time.sleep(random.uniform(0.5, 1.0))
            
            # Get profile meter
            self.profileMeter()
            time.sleep(random.uniform(0.5, 1.0))
            self.get_dynamic_ui_configuration()
            # Update prompt (exact HAR pattern)
            url = "https://api.gotinder.com/v2/profile/user"
            payload = {"selected_prompts": [{"id": prompt_id, "answer_text": prompt_text}]}
            
            headers = self.headers("json_post")
            json_data = json.dumps(payload)
            headers["Content-Length"] = str(len(json_data.encode('utf-8')))
            
            response = self._make_request('POST', url, headers=headers, data=json_data)
            
            if response and response.status_code == 200:
                self.invalidate_profile_cache()
                logging.info("Prompts updated successfully")
                
                # Get profile meter again after update (as in HAR)
                time.sleep(random.uniform(0.5, 1.0))
                self.profileMeter()
                
                return {"success": True, "operations": 1, "success_count": 1, "errors": []}
            else:
                return {"success": False, "operations": 1, "success_count": 0, "errors": ["Failed to update prompt"]}
                
        except Exception as e:
            logging.error(f"Error processing prompt: {e}")
            return {"success": False, "operations": 0, "success_count": 0, "errors": [str(e)]}
    
    def invalidate_profile_cache(self):
        """Invalidate profile cache"""
        self.profile_cache = None
        self.profile_cache_time = 0
    
    # SWIPING AND MATCHING METHODS
    
    def get_recommendations(self) -> Optional[List[Dict]]:
        """Get recommendation stack (exact HAR pattern)"""
        url = f"https://api.gotinder.com/v2/recs/core?locale=en&distance_setting=mi&duos=1"
        headers = self.headers("recs")
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                logging.debug("Recommendations not modified since last request")
                return []
            try:
                data = response.json()
                results = data.get("data", {}).get("results", [])
                logging.info(f"Got {len(results)} recommendations")
                return results
            except Exception as e:
                logging.error(f"Error parsing recommendations response: {e}")
                return []
        elif response and response.status_code == 400:
            logging.warning("No more recommendations available")
            return []
        return None
    
    def like_user(self, user_id: str, photo_id: Optional[str] = None, 
                  content_hash: Optional[str] = None, s_number: Optional[int] = None,
                  user_traveling: bool = True, fast_match: int = 1) -> Any:
        """Like a user with exact HAR payload format"""
        if not user_id:
            logging.error("No user_id provided for like")
            return False
        
        url = f"https://api.gotinder.com/like/{user_id}"
        
        # Build payload matching exact HAR format
        payload = {}
        
        if photo_id:
            payload["photoId"] = photo_id
        if content_hash:
            payload["content_hash"] = content_hash
        
        payload.update({
            "super": 0,
            "user_traveling": user_traveling,
            "fast_match": fast_match,
            "top_picks": 0,
            "undo": 0
        })
        
        if s_number is not None:
            payload["s_number"] = s_number
        if photo_id:
            payload["liked_content_id"] = photo_id
            payload["liked_content_type"] = "photo"
        
        # Prepare headers with exact HAR pattern
        headers = self.headers("like")
        headers["Content-Type"] = "application/json; charset=UTF-8"
        json_payload = json.dumps(payload)
        headers["Content-Length"] = str(len(json_payload.encode('utf-8')))
        
        logging.debug(f"Liking user {user_id} with payload: {json_payload}")
        
        response = self._make_request('POST', url, headers=headers, data=json_payload)
        
        if response:
            try:
                if response.status_code == 200:
                    result = response.json()
                    logging.debug(f"Like response: {json.dumps(result)[:500]}")
                    
                    # Check for match
                    if "match" in result:
                        if result["match"]:
                            #logging.info(f"🎉 MATCHED with user {user_id}!")
                            return "match"
                        else:
                            pass
                        return True
                    
                    # Check other success indicators
                    if "likes_remaining" in result or result.get("status") == 200:
                        pass
                        return True
                    
                    # Check for rate limiting
                    if "rate_limited_until" in result:
                        rate_limit_time = result['rate_limited_until']
                        pass
                        return False
                    
                    # Default to success if no explicit error
                    return True
                    
                elif response.status_code == 400:
                    try:
                        error_data = response.json()
                        error_message = error_data.get("error", {}).get("message", "Unknown error")
                        #logging.warning(f"Like failed (400): {error_message}")
                        
                        if "already liked" in error_message.lower():
                            return True  # Consider this a success
                        elif "rate limit" in error_message.lower():
                            return False
                        
                    except:
                        pass
                    return False
                    
                else:
                    pass
                    return False
                    
            except Exception as e:
                pass
                return False
        
        return False
    
    def pass_user(self, user_id: str, photo_id: Optional[str] = None, 
                  content_hash: Optional[str] = None, s_number: Optional[int] = None) -> bool:
        """Pass (dislike) a user with exact HAR payload format"""
        if not user_id:
            logging.error("No user_id provided for pass")
            return False
        
        url = f"https://api.gotinder.com/pass/{user_id}"
        
        # Build payload
        payload = {}
        
        if photo_id:
            payload["photoId"] = photo_id
        if content_hash:
            payload["content_hash"] = content_hash
        if s_number is not None:
            payload["s_number"] = s_number
        
        headers = self.headers("json_post")
        json_payload = json.dumps(payload)
        headers["Content-Length"] = str(len(json_payload.encode('utf-8')))
        
        response = self._make_request('POST', url, headers=headers, data=json_payload)
        
        if response and response.status_code == 200:
            logging.info(f"👎 Passed user {user_id}")
            return True
        
        return False
    
    # FAST MATCH / LIKES METHODS
    
    def liked_me_count(self) -> Optional[int]:
        """Get count of users who liked me (exact HAR pattern)"""
        url = "https://api.gotinder.com/v2/fast-match/count"
        headers = self.headers()
        
        response = self._make_request('GET', url, headers=headers)
        
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return getattr(self, '_cached_liked_me_count', 0)
            try:
                data = response.json()
                count = data.get("data", {}).get("count", 0)
                self._cached_liked_me_count = count
                return count
            except Exception as e:
                logging.error(f"Error parsing liked me count: {e}")
                return 0
        return None
    
    def liked_me(self, count: int = 20, page_token: Optional[str] = None) -> Optional[List[Dict]]:
        """Get users who liked me with pagination (exact HAR pattern)"""
        url = f"https://api.gotinder.com/v2/fast-match?count=20"
        if page_token:
            url += f"&page_token={page_token}"
        
        headers = self.headers("profile")
        
        response = self._make_request('GET', url, headers=headers)
        
        if not response:
            return None
        
        if response.status_code == 304:
            logging.info("No new liked_me users since last check")
            return []
        
        if response.status_code == 200:
            try:
                data = response.json()
                return data.get("data", {}).get("results", [])
            except Exception as e:
                logging.error(f"Error parsing liked_me response: {e}")
                return None
        
        return None
    
    def get_fast_match_teaser(self) -> Optional[Dict]:
        """Get fast match teaser (exact HAR pattern)"""
        url = "https://api.gotinder.com/v2/fast-match/teaser"
        headers = self.headers()
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return {"status": "not_modified"}
            try:
                return response.json()
            except:
                return None
        return None
    
    def get_fast_match_newcount(self, count_token: str) -> Optional[Dict]:
        """Get new fast match count with token (exact HAR pattern)"""
        url = f"https://api.gotinder.com/v2/fast-match/newcount?count_token={count_token}"
        headers = self.headers()
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code == 200:
            try:
                return response.json()
            except:
                return None
        return None
    
    def myLikes(self) -> Optional[Dict]:
        """Get my likes (exact HAR pattern)"""
        url = "https://api.gotinder.com/v2/my-likes"
        headers = self.headers("profile")
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return {"likes": []}
            try:
                return response.json()
            except Exception as e:
                logging.error(f"Error parsing my likes response: {e}")
                return None
        return None
    
    # MESSAGES AND MATCHES
    
    def get_inbox_messages(self) -> Optional[Dict]:
        """Get inbox messages (exact HAR pattern)"""
        url = "https://api.gotinder.com/v2/inbox/messages"
        headers = self.headers()
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return {"messages": []}
            try:
                return response.json()
            except:
                return {"messages": []}
        return None
    
    def get_received_messages(self) -> Optional[Dict]:
        """Get received messages (exact HAR pattern)"""
        url = "https://api.gotinder.com/v1/direct-messages/received-messages"
        headers = self.headers()
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return {"messages": []}
            try:
                return response.json()
            except:
                return None
        return None
    
    def get_matches(self, count: int = 100) -> Optional[List[Dict]]:
        """Get matches list (exact HAR pattern)"""
        url = f"https://api.gotinder.com/v2/matches?count={count}"
        headers = self.headers()
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return []
            try:
                data = response.json()
                return data.get("data", {}).get("matches", [])
            except:
                return []
        return None
    
    # SUBSCRIPTION AND FEATURE METHODS
    
    def get_subscription_features(self) -> Dict:
        """Get all subscription features (exact HAR pattern)"""
        features = {}
        
        # Swipe Surge
        url = "https://api.gotinder.com/v2/subscriptions/swipe_surge"
        response = self._make_request('GET', url)
        if response and response.status_code in [200, 304]:
            if response.status_code == 200:
                try:
                    features['swipe_surge'] = response.json()
                except:
                    features['swipe_surge'] = {}
        
        # Vibes
        url = "https://api.gotinder.com/v2/subscriptions/vibes"
        response = self._make_request('GET', url)
        if response and response.status_code in [200, 304]:
            if response.status_code == 200:
                try:
                    features['vibes'] = response.json()
                except:
                    features['vibes'] = {}
        
        return features
    
    def get_payment_methods(self) -> Optional[Dict]:
        """Get payment methods (exact HAR pattern)"""
        url = "https://api.gotinder.com/v2/purchase/payment-methods"
        headers = self.headers()
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return {"payment_methods": []}
            try:
                return response.json()
            except:
                return None
        return None
    
    # CAMPAIGNS AND CONTENT
    
    def get_campaigns(self, campaign_types: List[str] = None) -> Optional[Dict]:
        """Get Tinder campaigns (exact HAR pattern)"""
        if campaign_types is None:
            campaign_types = ['live_ops', 'mini_merch', 'modal']
        
        # URL encode the types parameter
        types_param = "%2C".join(campaign_types)
        
        url = f"https://api.gotinder.com/v2/insendio/campaigns?types={types_param}"
        headers = self.headers()
        
        response = self._make_request('GET', url, headers=headers)
        
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return {"campaigns": []}
            try:
                return response.json()
            except Exception as e:
                logging.error(f"Failed to parse campaigns response: {e}")
                return None
        
        return None
    
    def get_tappy_content(self) -> Optional[Dict]:
        """Get tappy content (exact HAR pattern)"""
        url = "https://api.gotinder.com/dynamicui/tappycontent"
        headers = self.headers()
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            try:
                return response.json() if response.status_code == 200 else {}
            except:
                return {}
        return None
    
    def get_duos(self) -> Optional[Dict]:
        """Get Tinder duos (exact HAR pattern)"""
        url = "https://api.gotinder.com/v1/duos"
        headers = self.headers()
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return {"status": "not_modified"}
            try:
                return response.json()
            except:
                return None
        return None
    
    def get_dynamic_ui_configuration(self, component_id="prompts_text_editor_v2") -> Optional[Dict]:
        """Get dynamic UI configuration for specific components"""
        url = f"https://api.gotinder.com/v2/dynamicui/configuration/content?component_id={component_id}"
        headers = self.headers()
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return {"status": "not_modified"}
            try:
                return response.json()
            except:
                return None
        return None
    
    def get_subscriptions_readreceipts(self) -> Optional[Dict]:
        """Get read receipts subscription info"""
        url = "https://api.gotinder.com/v2/subscriptions/readreceipts"
        headers = self.headers()
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return {"status": "not_modified"}
            try:
                return response.json()
            except:
                return None
        return None
    
    def get_tinder_u_profile(self) -> Optional[Dict]:
        """Get Tinder U (university) profile info"""
        url = "https://api.gotinder.com/v2/profile?include=tinder_u"
        headers = self.headers("profile")
        
        response = self._make_request('GET', url, headers=headers)
        if response and response.status_code in [200, 304]:
            if response.status_code == 304:
                return {"status": "not_modified"}
            try:
                return response.json()
            except:
                return None
        return None
    
    def update_user_preferences(self, age_filter_min: int = 18, age_filter_max: int = 32, 
                              distance_filter: int = 44, show_same_orientation_first: bool = True) -> bool:
        """Update user search preferences (exact HAR pattern)"""
        url = "https://api.gotinder.com/v2/profile/user"
        
        payload = {
            "age_filter_min": age_filter_min,
            "age_filter_max": age_filter_max,
            "distance_filter": distance_filter,
            "show_same_orientation_first": {}
        }
        
        headers = self.headers("json_post")
        json_payload = json.dumps(payload)
        headers["Content-Length"] = str(len(json_payload.encode('utf-8')))
        
        response = self._make_request('POST', url, headers=headers, data=json_payload)
        if response and response.status_code == 200:
            self.invalidate_profile_cache()
            logging.info("User preferences updated successfully")
            return True
        return False
    
    # LOCATION METHODS
    
    def get_current_passport_location(self) -> Optional[Tuple[float, float, str]]:
        """Get current passport location from profile"""
        if not self.profile_cache:
            self.profile()
        
        try:
            travel_data = self.profile_cache.get("data", {}).get("travel", {})
            if travel_data and travel_data.get("is_traveling"):
                pos = travel_data.get("travel_pos", {})
                info = travel_data.get("travel_location_info", [])
                
                if pos and info:
                    lat = pos.get("lat")
                    lon = pos.get("lon")
                    
                    if info and len(info) > 0:
                        location_info = info[0]
                        city = location_info.get("locality", {}).get("long_name", "Unknown")
                        country = location_info.get("country", {}).get("long_name", "")
                        location_name = f"{city}, {country}" if country else city
                    else:
                        location_name = "Unknown location"
                    
                    if lat is not None and lon is not None:
                        logging.info(f"Current passport location: {location_name} ({lat}, {lon})")
                        return lat, lon, location_name
        except Exception as e:
            logging.error(f"Error getting passport location: {e}")
        
        return None
    
    def set_passport_location(self, latitude: float, longitude: float) -> bool:
        """Set passport location (exact HAR pattern)"""
        # Validate coordinates
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            logging.error(f"Invalid coordinates: lat={latitude}, lon={longitude}")
            return False
        
        url = "https://api.gotinder.com/passport/user/travel"
        payload = {"lat": latitude, "lon": longitude}
        
        headers = self.headers("json_post")
        json_data = json.dumps(payload)
        headers["Content-Length"] = str(len(json_data.encode('utf-8')))
        
        response = self._make_request('POST', url, headers=headers, data=json_data)
        
        if response:
            if response.status_code == 200:
                self.invalidate_profile_cache()
                logging.info(f"Passport location set to ({latitude}, {longitude})")
                return True
            elif response.status_code == 400:
                logging.warning("Failed to set passport location - account may not have Gold/Plus")
                return False
        
        return False
    
    # AUTHENTICATION METHODS
    
    def auth_login(self) -> Optional[Dict]:
        """Authenticate using refresh token with manual protobuf encoding"""
        url = "https://api.gotinder.com/v3/auth/login"
        headers = self.headers("auth")
        
        try:
            #logging.info(f"Attempting authentication...")
            
            # Manual protobuf encoding for refresh auth
            protobuf_data = self._encode_refresh_auth_protobuf(self.refresh_token)
            
            response = requests_go.post(url, headers=headers, data=protobuf_data,
                                   proxies=self.proxies, tls_config=tls_config.to_tls_config(tls_settings()), timeout=30)
            
            
            
            if(response.status_code == 403):
                        print("🚫 Banned account")
            if(response.status_code == 401):
                        print("🚫 Dead Auth account")
            if response.status_code == 200:
                result = self._parse_auth_response_manual(response.content)
                
                if result and result.get("success") and result.get("auth_token"):
                    self.auth_token = result["auth_token"]
                    if result.get("refresh_token"):
                        self.refresh_token = result["refresh_token"]
                   # logging.info("Auth token refreshed successfully")
                    return result
                else:
                    
                   # logging.error(f"Auth failed: {result}")
                   pass
                    
            else:
               # logging.error(f"Auth failed with status {response.status_code}")
                #logging.debug(f"Response: {response.text[:500]}")
                pass
            return None
            
        except Exception as e:
            logging.error(f"Auth exception: {e}")
            logging.debug(traceback.format_exc())
            return None
    
    def _encode_refresh_auth_protobuf(self, refresh_token: str) -> bytes:
        """Manual protobuf encoding for auth request"""
        refresh_token_bytes = refresh_token.encode('utf-8')
        refresh_token_field = bytes([0x0A]) + self._encode_varint(len(refresh_token_bytes)) + refresh_token_bytes
        refresh_auth_field = bytes([0x52]) + self._encode_varint(len(refresh_token_field)) + refresh_token_field
        return refresh_auth_field
    
    def _parse_auth_response_manual(self, response_data: bytes) -> Dict:
        """Manual protobuf parsing for auth response"""
        try:
            result = {"success": True, "auth_token": None, "refresh_token": None, "user_id": None}
            
            pos = 0
            while pos < len(response_data):
                field_key = response_data[pos]
                pos += 1
                field_num = field_key >> 3
                
                if field_num == 8:  # LoginResult
                    length, pos = self._decode_varint(response_data, pos)
                    login_data = response_data[pos:pos + length]
                    pos += length
                    
                    # Parse login result fields
                    lr_pos = 0
                    while lr_pos < len(login_data):
                        lr_key = login_data[lr_pos]
                        lr_pos += 1
                        lr_field_num = lr_key >> 3
                        
                        if lr_field_num == 1:  # refresh_token
                            str_len, lr_pos = self._decode_varint(login_data, lr_pos)
                            result["refresh_token"] = login_data[lr_pos:lr_pos + str_len].decode('utf-8')
                            lr_pos += str_len
                        elif lr_field_num == 2:  # auth_token
                            str_len, lr_pos = self._decode_varint(login_data, lr_pos)
                            result["auth_token"] = login_data[lr_pos:lr_pos + str_len].decode('utf-8')
                            lr_pos += str_len
                        elif lr_field_num == 4:  # user_id
                            str_len, lr_pos = self._decode_varint(login_data, lr_pos)
                            result["user_id"] = login_data[lr_pos:lr_pos + str_len].decode('utf-8')
                            lr_pos += str_len
                        else:
                            # Skip unknown fields
                            if (lr_key & 0x7) == 2:  # length-delimited
                                skip_len, lr_pos = self._decode_varint(login_data, lr_pos)
                                lr_pos += skip_len
                            elif (lr_key & 0x7) == 0:  # varint
                                _, lr_pos = self._decode_varint(login_data, lr_pos)
                            else:
                                lr_pos += 1
                elif field_num == 7:  # Error
                    length, pos = self._decode_varint(response_data, pos)
                    error_data = response_data[pos:pos + length]
                    pos += length
                    
                    # Parse error
                    error_pos = 0
                    error_message = ""
                    while error_pos < len(error_data):
                        error_key = error_data[error_pos]
                        error_pos += 1
                        error_field_num = error_key >> 3
                        
                        if error_field_num == 1:  # message
                            str_len, error_pos = self._decode_varint(error_data, error_pos)
                            error_message = error_data[error_pos:error_pos + str_len].decode('utf-8')
                            error_pos += str_len
                        else:
                            # Skip unknown fields
                            if (error_key & 0x7) == 2:
                                skip_len, error_pos = self._decode_varint(error_data, error_pos)
                                error_pos += skip_len
                            else:
                                error_pos += 1
                    
                    return {"success": False, "error": error_message}
                else:
                    # Skip other fields
                    wire_type = field_key & 0x7
                    if wire_type == 2:  # length-delimited
                        skip_len, pos = self._decode_varint(response_data, pos)
                        pos += skip_len
                    elif wire_type == 0:  # varint
                        _, pos = self._decode_varint(response_data, pos)
                    else:
                        pos += 1
            
            return result
            
        except Exception as e:
            logging.error(f"Manual protobuf parsing error: {e}")
            return {"success": False, "error": str(e)}
    
    def _encode_varint(self, value: int) -> bytes:
        """Encode varint for protobuf"""
        result = []
        while value >= 0x80:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)
        return bytes(result)
    
    def _decode_varint(self, data: bytes, pos: int) -> Tuple[int, int]:
        """Decode varint from protobuf"""
        result = 0
        shift = 0
        while pos < len(data):
            byte = data[pos]
            pos += 1
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7
        return result, pos   
    
