#!/usr/bin/env python3
"""
ACI Fabric Client
Handles connections to APIC REST API and NX-OS devices for data collection
"""

import requests
import json
import paramiko
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings for demo purposes
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Represents a fabric device from inventory"""
    name: str
    hostname: str
    device_type: str  # apic, spine, leaf
    node_id: Optional[str] = None
    priority: Optional[int] = None


class APICClient:
    """APIC REST API client with authentication and session management"""
    
    def __init__(self, hostname: str, username: str, password: str, timeout: int = 30):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout
        self.base_url = f"https://{hostname}"
        self.session = requests.Session()
        self.session.verify = False
        self.auth_token = None
        self.is_authenticated = False
        
    def authenticate(self) -> bool:
        """Authenticate with APIC and establish session"""
        auth_url = f"{self.base_url}/api/aaaLogin.json"
        auth_data = {
            "aaaUser": {
                "attributes": {
                    "name": self.username,
                    "pwd": self.password
                }
            }
        }
        
        try:
            response = self.session.post(auth_url, json=auth_data, timeout=self.timeout)
            response.raise_for_status()
            
            auth_response = response.json()
            if "imdata" in auth_response and len(auth_response["imdata"]) > 0:
                self.auth_token = auth_response["imdata"][0]["aaaLogin"]["attributes"]["token"]
                self.is_authenticated = True
                logger.info(f"Successfully authenticated to APIC {self.hostname}")
                return True
            else:
                logger.error(f"Authentication failed for APIC {self.hostname}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error to APIC {self.hostname}: {e}")
            return False
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Authentication response parsing error for APIC {self.hostname}: {e}")
            return False
    
    def get_data(self, endpoint: str, params: Dict = None) -> Optional[Dict[str, Any]]:
        """Retrieve data from APIC REST API endpoint"""
        if not self.is_authenticated:
            logger.error(f"Not authenticated to APIC {self.hostname}")
            return None
            
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Successfully retrieved data from {endpoint} on APIC {self.hostname}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error retrieving data from {endpoint} on APIC {self.hostname}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {endpoint} on APIC {self.hostname}: {e}")
            return None
    
    def logout(self):
        """Logout from APIC and clear session"""
        if self.is_authenticated:
            try:
                logout_url = f"{self.base_url}/api/aaaLogout.json"
                self.session.post(logout_url, timeout=10)
                logger.info(f"Logged out from APIC {self.hostname}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error during logout from APIC {self.hostname}: {e}")
            finally:
                self.is_authenticated = False
                self.auth_token = None


class NXOSClient:
    """NX-OS SSH client for direct switch command execution"""
    
    def __init__(self, hostname: str, username: str, password: str, timeout: int = 30):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout
        self.ssh_client = None
        self.is_connected = False
    
    def connect(self) -> bool:
        """Establish SSH connection to NX-OS device"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.ssh_client.connect(
                hostname=self.hostname,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False
            )
            
            self.is_connected = True
            logger.info(f"Successfully connected to NX-OS device {self.hostname}")
            return True
            
        except Exception as e:
            logger.error(f"SSH connection failed to {self.hostname}: {e}")
            return False
    
    def execute_command(self, command: str) -> Optional[str]:
        """Execute command on NX-OS device and return output"""
        if not self.is_connected:
            logger.error(f"Not connected to NX-OS device {self.hostname}")
            return None
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=self.timeout)
            
            # Wait for command completion
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status == 0:
                output = stdout.read().decode('utf-8')
                logger.debug(f"Successfully executed '{command}' on {self.hostname}")
                return output
            else:
                error = stderr.read().decode('utf-8')
                logger.error(f"Command '{command}' failed on {self.hostname}: {error}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing command '{command}' on {self.hostname}: {e}")
            return None
    
    def execute_commands(self, commands: List[str]) -> Dict[str, str]:
        """Execute multiple commands and return results dictionary"""
        results = {}
        
        for command in commands:
            output = self.execute_command(command)
            if output is not None:
                results[command] = output
            else:
                results[command] = ""  # Empty string for failed commands
        
        return results
    
    def disconnect(self):
        """Close SSH connection"""
        if self.ssh_client:
            try:
                self.ssh_client.close()
                logger.info(f"Disconnected from NX-OS device {self.hostname}")
            except Exception as e:
                logger.warning(f"Error during disconnect from {self.hostname}: {e}")
            finally:
                self.is_connected = False
                self.ssh_client = None


class FabricClient:
    """High-level client for managing connections to entire ACI fabric"""
    
    def __init__(self, apic_devices: List[DeviceInfo], username: str, password: str):
        self.apic_devices = sorted(apic_devices, key=lambda x: x.priority or 1)
        self.username = username
        self.password = password
        self.primary_apic = None
        self.device_clients = {}
        
    def connect(self) -> bool:
        """Connect to fabric via primary APIC with failover"""
        return self.connect_to_fabric()
    
    def connect_to_fabric(self) -> bool:
        """Connect to fabric via primary APIC with failover"""
        for apic_device in self.apic_devices:
            apic_client = APICClient(apic_device.hostname, self.username, self.password)
            
            if apic_client.authenticate():
                self.primary_apic = apic_client
                logger.info(f"Successfully connected to primary APIC: {apic_device.hostname}")
                return True
            else:
                logger.warning(f"Failed to connect to APIC: {apic_device.hostname}")
        
        logger.error("Failed to connect to any APIC in the fabric")
        return False
    
    def get_fabric_data(self, endpoint: str, params: Dict = None) -> Optional[Dict[str, Any]]:
        """Retrieve fabric-wide data via primary APIC"""
        if not self.primary_apic:
            logger.error("No primary APIC connection available")
            return None
        
        return self.primary_apic.get_data(endpoint, params)
    
    def connect_to_device(self, device: DeviceInfo) -> Optional[NXOSClient]:
        """Connect to specific fabric device via SSH"""
        if device.name in self.device_clients:
            return self.device_clients[device.name]
        
        nxos_client = NXOSClient(device.hostname, self.username, self.password)
        
        if nxos_client.connect():
            self.device_clients[device.name] = nxos_client
            return nxos_client
        else:
            logger.error(f"Failed to connect to device {device.name} ({device.hostname})")
            return None
    
    def disconnect_all(self):
        """Disconnect from all fabric devices"""
        # Disconnect from APIC
        if self.primary_apic:
            self.primary_apic.logout()
            self.primary_apic = None
        
        # Disconnect from all NX-OS devices
        for device_name, client in self.device_clients.items():
            client.disconnect()
        
        self.device_clients.clear()
        logger.info("Disconnected from all fabric devices")