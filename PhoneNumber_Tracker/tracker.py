#!/usr/bin/env python3
"""
Google Maps Navigation System v4.0
Complete implementation using ONLY Google Maps APIs
"""

import webbrowser
import requests
import json
import os
import sys
import time
from datetime import datetime
from typing import Tuple, Dict, List
from dataclasses import dataclass
from enum import Enum
import logging
import csv
import math

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TransportMode(Enum):
    DRIVING = "driving"
    WALKING = "walking"
    BICYCLING = "bicycling"
    TRANSIT = "transit"
    FLYING = "flying"

@dataclass
class Location:
    latitude: float
    longitude: float
    name: str
    formatted_address: str
    place_id: str
    types: List[str]

@dataclass
class RouteInfo:
    distance_meters: int
    duration_seconds: int
    distance_text: str
    duration_text: str
    steps: List[Dict]
    polyline: str
    warnings: List[str]

@dataclass
class PlaceDetails:
    name: str
    address: str
    phone: str
    website: str
    opening_hours: List[str]
    rating: float
    reviews: List[Dict]
    photos: List[str]

class GoogleMapsAPI:
    """Complete Google Maps API implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_urls = {
            'geocode': 'https://maps.googleapis.com/maps/api/geocode/json',
            'directions': 'https://maps.googleapis.com/maps/api/directions/json',
            'places': 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json',
            'place_details': 'https://maps.googleapis.com/maps/api/place/details/json',
            'distance_matrix': 'https://maps.googleapis.com/maps/api/distancematrix/json',
            'elevation': 'https://maps.googleapis.com/maps/api/elevation/json',
            'timezone': 'https://maps.googleapis.com/maps/api/timezone/json',
            'static_map': 'https://maps.googleapis.com/maps/api/staticmap',
            'streetview': 'https://maps.googleapis.com/maps/api/streetview'
        }
        self.session = requests.Session()
        self.cache = {}
        
    def make_request(self, endpoint: str, params: Dict) -> Dict:
        """Make API request with error handling"""
        cache_key = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        params['key'] = self.api_key
        
        try:
            response = self.session.get(self.base_urls[endpoint], params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') not in ['OK', 'ZERO_RESULTS']:
                error_msg = data.get('error_message', 'Unknown error')
                raise Exception(f"Google API Error: {data.get('status')} - {error_msg}")
            
            self.cache[cache_key] = data
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode failed: {e}")
            raise
    
    def geocode(self, address: str) -> List[Location]:
        """Convert address to coordinates"""
        params = {
            'address': address,
            'language': 'en'
        }
        
        data = self.make_request('geocode', params)
        locations = []
        
        for result in data.get('results', []):
            location = Location(
                latitude=result['geometry']['location']['lat'],
                longitude=result['geometry']['location']['lng'],
                name=result.get('formatted_address', address),
                formatted_address=result.get('formatted_address', ''),
                place_id=result.get('place_id', ''),
                types=result.get('types', [])
            )
            locations.append(location)
        
        return locations
    
    def reverse_geocode(self, lat: float, lng: float) -> List[Location]:
        """Convert coordinates to address"""
        params = {
            'latlng': f"{lat},{lng}",
            'language': 'en',
            'result_type': 'street_address|political'
        }
        
        data = self.make_request('geocode', params)
        locations = []
        
        for result in data.get('results', []):
            location = Location(
                latitude=lat,
                longitude=lng,
                name=result.get('formatted_address', f"{lat},{lng}"),
                formatted_address=result.get('formatted_address', ''),
                place_id=result.get('place_id', ''),
                types=result.get('types', [])
            )
            locations.append(location)
        
        return locations
    
    def get_directions(self, origin: str, destination: str, mode: TransportMode = TransportMode.DRIVING,
                      alternatives: bool = True, avoid: List[str] = None, 
                      units: str = 'metric', departure_time: str = 'now',
                      traffic_model: str = 'best_guess') -> List[RouteInfo]:
        """Get directions between two points"""
        params = {
            'origin': origin,
            'destination': destination,
            'mode': mode.value,
            'alternatives': 'true' if alternatives else 'false',
            'units': units,
            'departure_time': departure_time,
            'traffic_model': traffic_model,
            'language': 'en'
        }
        
        if avoid:
            params['avoid'] = '|'.join(avoid)
        
        data = self.make_request('directions', params)
        routes = []
        
        for route in data.get('routes', []):
            leg = route['legs'][0]
            
            steps = []
            for step in leg['steps']:
                step_info = {
                    'instruction': step['html_instructions'].replace('<b>', '').replace('</b>', ''),
                    'distance': step['distance']['text'],
                    'duration': step['duration']['text'],
                    'start_location': step['start_location'],
                    'end_location': step['end_location']
                }
                steps.append(step_info)
            
            route_info = RouteInfo(
                distance_meters=leg['distance']['value'],
                duration_seconds=leg['duration']['value'],
                distance_text=leg['distance']['text'],
                duration_text=leg['duration']['text'],
                steps=steps,
                polyline=route['overview_polyline']['points'],
                warnings=route.get('warnings', [])
            )
            routes.append(route_info)
        
        return routes
    
    def get_distance_matrix(self, origins: List[str], destinations: List[str], 
                           mode: TransportMode = TransportMode.DRIVING) -> Dict:
        """Calculate distance matrix between multiple points"""
        params = {
            'origins': '|'.join(origins),
            'destinations': '|'.join(destinations),
            'mode': mode.value,
            'units': 'metric',
            'language': 'en'
        }
        
        data = self.make_request('distance_matrix', params)
        return data
    
    def find_places(self, query: str, location: Tuple[float, float] = None, 
                   radius: int = 5000, type: str = None) -> List[Dict]:
        """Find places near location"""
        params = {
            'input': query,
            'inputtype': 'textquery',
            'fields': 'formatted_address,name,geometry,place_id,types',
            'language': 'en'
        }
        
        if location:
            params['locationbias'] = f"point:{location[0]},{location[1]}"
        
        if radius:
            params['radius'] = str(radius)
        
        if type:
            params['type'] = type
        
        data = self.make_request('places', params)
        return data.get('candidates', [])
    
    def get_place_details(self, place_id: str) -> PlaceDetails:
        """Get detailed information about a place"""
        params = {
            'place_id': place_id,
            'fields': 'name,formatted_address,formatted_phone_number,website,opening_hours,rating,review,photo',
            'language': 'en'
        }
        
        data = self.make_request('place_details', params)
        result = data.get('result', {})
        
        return PlaceDetails(
            name=result.get('name', ''),
            address=result.get('formatted_address', ''),
            phone=result.get('formatted_phone_number', ''),
            website=result.get('website', ''),
            opening_hours=result.get('opening_hours', {}).get('weekday_text', []),
            rating=result.get('rating', 0.0),
            reviews=result.get('reviews', []),
            photos=[photo.get('photo_reference', '') for photo in result.get('photos', [])]
        )
    
    def get_elevation(self, locations: List[Tuple[float, float]]) -> List[Dict]:
        """Get elevation data for locations"""
        locations_str = '|'.join([f"{lat},{lng}" for lat, lng in locations])
        params = {'locations': locations_str}
        
        data = self.make_request('elevation', params)
        return data.get('results', [])
    
    def get_timezone(self, location: Tuple[float, float], timestamp: int = None) -> Dict:
        """Get timezone information for location"""
        if timestamp is None:
            timestamp = int(time.time())
        
        params = {
            'location': f"{location[0]},{location[1]}",
            'timestamp': timestamp
        }
        
        data = self.make_request('timezone', params)
        return data
    
    def generate_static_map(self, center: Tuple[float, float], zoom: int = 12, 
                           size: Tuple[int, int] = (600, 400), markers: List[Tuple[float, float]] = None,
                           path: str = None, style: str = None) -> str:
        """Generate static map URL"""
        params = {
            'center': f"{center[0]},{center[1]}",
            'zoom': str(zoom),
            'size': f"{size[0]}x{size[1]}",
            'scale': '2',
            'format': 'png',
            'maptype': 'roadmap'
        }
        
        if markers:
            markers_str = '|'.join([f"{lat},{lng}" for lat, lng in markers])
            params['markers'] = f"color:red|{markers_str}"
        
        if path:
            params['path'] = path
        
        if style:
            params['style'] = style
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_urls['static_map']}?{query_string}&key={self.api_key}"
    
    def generate_streetview(self, location: Tuple[float, float], size: Tuple[int, int] = (600, 400),
                           heading: int = 0, pitch: int = 0, fov: int = 90) -> str:
        """Generate street view URL"""
        params = {
            'location': f"{location[0]},{location[1]}",
            'size': f"{size[0]}x{size[1]}",
            'heading': str(heading),
            'pitch': str(pitch),
            'fov': str(fov)
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_urls['streetview']}?{query_string}&key={self.api_key}"

class NavigationManager:
    """Complete navigation management"""
    
    def __init__(self, api: GoogleMapsAPI):
        self.api = api
        self.history = []
        self.favorites = []
        
    def generate_maps_url(self, origin: str, destination: str, mode: TransportMode = TransportMode.DRIVING) -> str:
        """Generate Google Maps URL"""
        base_url = "https://www.google.com/maps/dir/"
        
        # Encode parameters
        origin_encoded = origin.replace(' ', '+')
        dest_encoded = destination.replace(' ', '+')
        
        mode_param = {
            TransportMode.DRIVING: "driving",
            TransportMode.WALKING: "walking",
            TransportMode.BICYCLING: "bicycling",
            TransportMode.TRANSIT: "transit",
            TransportMode.FLYING: ""
        }.get(mode, "driving")
        
        if mode == TransportMode.FLYING:
            return f"{base_url}{origin_encoded}/{dest_encoded}/@api=1&travelmode=flying"
        else:
            return f"{base_url}{origin_encoded}/{dest_encoded}/data=!3m1!4b1!4m2!4m1!3e2"
    
    def navigate(self, origin: str, destination: str, mode: TransportMode = TransportMode.DRIVING,
                open_browser: bool = True, get_details: bool = True) -> Dict:
        """Complete navigation workflow"""
        
        print(f"\n🚗 Calculating route from {origin} to {destination}...")
        
        # Get directions
        routes = self.api.get_directions(origin, destination, mode)
        
        if not routes:
            raise Exception("No routes found")
        
        route = routes[0]
        
        # Get origin and destination details
        origin_details = self.api.geocode(origin)[0] if get_details else None
        dest_details = self.api.geocode(destination)[0] if get_details else None
        
        # Generate map URL
        maps_url = self.generate_maps_url(origin, destination, mode)
        
        # Display route information
        print(f"\n📏 Route Information:")
        print(f"   Distance: {route.distance_text}")
        print(f"   Duration: {route.duration_text}")
        print(f"   Mode: {mode.value.capitalize()}")
        
        if route.warnings:
            print(f"\n⚠️  Warnings:")
            for warning in route.warnings:
                print(f"   • {warning}")
        
        # Display step-by-step instructions
        if len(route.steps) <= 10:
            print(f"\n📍 Turn-by-turn directions:")
            for i, step in enumerate(route.steps, 1):
                print(f"   {i}. {step['instruction']} ({step['distance']}, {step['duration']})")
        
        # Get additional info if requested
        if get_details and origin_details and dest_details:
            print(f"\n📍 Origin: {origin_details.formatted_address}")
            print(f"📍 Destination: {dest_details.formatted_address}")
            
            # Get elevation data
            elevations = self.api.get_elevation([
                (origin_details.latitude, origin_details.longitude),
                (dest_details.latitude, dest_details.longitude)
            ])
            
            if elevations:
                print(f"\n🏔️ Elevation:")
                print(f"   Origin: {elevations[0]['elevation']:.1f}m")
                print(f"   Destination: {elevations[1]['elevation']:.1f}m")
        
        # Get timezone info
        if dest_details:
            timezone = self.api.get_timezone((dest_details.latitude, dest_details.longitude))
            if timezone.get('timeZoneId'):
                print(f"\n🕐 Destination timezone: {timezone['timeZoneId']}")
        
        # Generate static map
        if origin_details and dest_details:
            static_map_url = self.api.generate_static_map(
                center=(
                    (origin_details.latitude + dest_details.latitude) / 2,
                    (origin_details.longitude + dest_details.longitude) / 2
                ),
                zoom=10,
                markers=[
                    (origin_details.latitude, origin_details.longitude),
                    (dest_details.latitude, dest_details.longitude)
                ],
                path=f"color:0x0000ff|weight:5|enc:{route.polyline}"
            )
            
            print(f"\n🗺️ Static map URL: {static_map_url}")
        
        print(f"\n🌐 Google Maps URL: {maps_url}")
        
        # Save to history
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'origin': origin,
            'destination': destination,
            'mode': mode.value,
            'distance': route.distance_text,
            'duration': route.duration_text,
            'maps_url': maps_url
        }
        self.history.append(history_entry)
        
        # Open in browser
        if open_browser:
            print("\nOpening Google Maps in browser...")
            webbrowser.open(maps_url)
        
        return {
            'route': route,
            'maps_url': maps_url,
            'origin_details': origin_details,
            'dest_details': dest_details
        }
    
    def search_nearby(self, location: str, query: str, radius: int = 5000) -> List[Dict]:
        """Search for places near location"""
        print(f"\n🔍 Searching for '{query}' near {location}...")
        
        # Get location coordinates
        locations = self.api.geocode(location)
        if not locations:
            raise Exception("Location not found")
        
        loc_coords = (locations[0].latitude, locations[0].longitude)
        
        # Find places
        places = self.api.find_places(query, loc_coords, radius)
        
        print(f"\nFound {len(places)} places:")
        for i, place in enumerate(places[:10], 1):
            print(f"   {i}. {place.get('name')} - {place.get('formatted_address', 'No address')}")
        
        return places
    
    def save_history(self):
        """Save navigation history to CSV"""
        if not self.history:
            return
        
        filename = f"navigation_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'origin', 'destination', 'mode', 
                'distance', 'duration', 'maps_url'
            ])
            writer.writeheader()
            writer.writerows(self.history)
        
        print(f"\n💾 History saved to {filename}")
    
    def show_history(self):
        """Display navigation history"""
        if not self.history:
            print("\nNo navigation history yet.")
            return
        
        print(f"\n📜 Navigation History ({len(self.history)} entries):")
        print("="*80)
        
        for i, entry in enumerate(self.history[-10:], 1):
            date = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M')
            print(f"{i}. {date}")
            print(f"   From: {entry['origin'][:50]}...")
            print(f"   To: {entry['destination'][:50]}...")
            print(f"   Mode: {entry['mode'].capitalize()}")
            print(f"   Distance: {entry['distance']}")
            print(f"   Duration: {entry['duration']}")
            print()

class GoogleMapsNavigator:
    """Main application"""
    
    def __init__(self):
        self.api_key = None
        self.api = None
        self.nav_manager = None
        self.load_config()
    
    def load_config(self):
        """Load API key from config file"""
        config_file = "google_maps_config.json"
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.api_key = config.get('api_key')
        
        if not self.api_key:
            self.setup_api_key()
    
    def setup_api_key(self):
        """Setup Google Maps API key"""
        print("\n" + "="*60)
        print("GOOGLE MAPS API SETUP")
        print("="*60)
        
        print("\nYou need a Google Maps API key:")
        print("1. Go to: https://console.cloud.google.com/google/maps-apis")
        print("2. Create a project")
        print("3. Enable these APIs:")
        print("   • Maps JavaScript API")
        print("   • Directions API")
        print("   • Geocoding API")
        print("   • Places API")
        print("   • Distance Matrix API")
        print("4. Create API credentials")
        print("5. Copy your API key")
        
        api_key = input("\nEnter your Google Maps API key: ").strip()
        
        if not api_key:
            print("\n❌ API key is required!")
            sys.exit(1)
        
        # Test the API key
        print("\nTesting API key...")
        try:
            test_api = GoogleMapsAPI(api_key)
            test_api.geocode("New York")
            print("✅ API key is valid!")
        except Exception as e:
            print(f"❌ API key test failed: {e}")
            sys.exit(1)
        
        self.api_key = api_key
        
        # Save to config
        config = {'api_key': api_key}
        with open("google_maps_config.json", 'w') as f:
            json.dump(config, f, indent=2)
        
        print("\n✅ API key saved to google_maps_config.json")
    
    def print_banner(self):
        """Print application banner"""
        banner = """
╔══════════════════════════════════════════════════════════╗
║              GOOGLE MAPS NAVIGATION SYSTEM v4.0          ║
║                 Complete Google Maps Integration          ║
╚══════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    def get_location_input(self, prompt: str) -> str:
        """Get location input from user"""
        while True:
            location = input(f"\n{prompt}: ").strip()
            if location:
                return location
            print("Location cannot be empty!")
    
    def select_transport_mode(self) -> TransportMode:
        """Let user select transport mode"""
        print("\nSelect transport mode:")
        print("1. 🚗 Driving")
        print("2. 🚶 Walking")
        print("3. 🚲 Bicycling")
        print("4. 🚆 Transit")
        print("5. ✈️ Flying")
        
        while True:
            choice = input("\nChoice (1-5, default 1): ").strip()
            if not choice:
                return TransportMode.DRIVING
            
            modes = {
                '1': TransportMode.DRIVING,
                '2': TransportMode.WALKING,
                '3': TransportMode.BICYCLING,
                '4': TransportMode.TRANSIT,
                '5': TransportMode.FLYING
            }
            
            if choice in modes:
                return modes[choice]
            
            print("Invalid choice!")
    
    def quick_navigation(self):
        """Quick navigation mode"""
        print("\n" + "="*60)
        print("QUICK NAVIGATION")
        print("="*60)
        
        origin = self.get_location_input("Enter starting point (address or coordinates)")
        destination = self.get_location_input("Enter destination (address or coordinates)")
        mode = self.select_transport_mode()
        
        try:
            self.nav_manager.navigate(origin, destination, mode)
        except Exception as e:
            print(f"\n❌ Navigation failed: {e}")
    
    def search_places(self):
        """Search for places"""
        print("\n" + "="*60)
        print("PLACE SEARCH")
        print("="*60)
        
        location = self.get_location_input("Enter location to search near")
        query = input("What are you looking for? (e.g., restaurants, hotels, gas stations): ").strip()
        
        try:
            self.nav_manager.search_nearby(location, query)
        except Exception as e:
            print(f"\n❌ Search failed: {e}")
    
    def multi_destination_trip(self):
        """Plan trip with multiple destinations"""
        print("\n" + "="*60)
        print("MULTI-DESTINATION TRIP")
        print("="*60)
        
        origin = self.get_location_input("Enter starting point")
        destinations = []
        
        print("\nEnter destinations (type 'done' when finished):")
        while True:
            dest = input(f"Destination {len(destinations) + 1}: ").strip()
            if dest.lower() == 'done':
                break
            if dest:
                destinations.append(dest)
        
        if not destinations:
            print("\nNo destinations entered!")
            return
        
        mode = self.select_transport_mode()
        
        print(f"\nPlanning trip with {len(destinations)} destinations...")
        
        # Calculate route for each segment
        current_origin = origin
        total_distance = 0
        total_duration = 0
        
        for i, destination in enumerate(destinations, 1):
            print(f"\n📍 Leg {i}: {current_origin} → {destination}")
            
            try:
                routes = self.api.get_directions(current_origin, destination, mode)
                if routes:
                    route = routes[0]
                    total_distance += route.distance_meters
                    total_duration += route.duration_seconds
                    
                    print(f"   Distance: {route.distance_text}")
                    print(f"   Duration: {route.duration_text}")
                    
                    # Generate URL for this segment
                    maps_url = self.nav_manager.generate_maps_url(current_origin, destination, mode)
                    print(f"   Maps URL: {maps_url}")
                    
                    # Update origin for next leg
                    current_origin = destination
                else:
                    print(f"   ❌ Could not find route")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print(f"\n📊 Trip Summary:")
        print(f"   Total distance: {total_distance / 1000:.1f} km")
        print(f"   Total duration: {total_duration / 3600:.1f} hours")
        
        # Generate complete trip URL
        waypoints = '|'.join(destinations[:-1])
        full_url = f"https://www.google.com/maps/dir/{origin}/{destinations[-1]}/"
        if waypoints:
            full_url += f"data=!3m1!4b1!4m2!4m1!3e2!5s{waypoints}"
        
        print(f"\n🌐 Complete trip URL: {full_url}")
        
        open_map = input("\nOpen complete trip in Google Maps? (y/n): ").strip().lower()
        if open_map == 'y':
            webbrowser.open(full_url)
    
    def batch_navigation(self):
        """Process multiple routes from file"""
        print("\n" + "="*60)
        print("BATCH NAVIGATION")
        print("="*60)
        
        filepath = input("Enter path to CSV file with routes: ").strip()
        
        if not os.path.exists(filepath):
            print("File not found!")
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                routes = list(reader)
            
            if not routes:
                print("No routes found in file!")
                return
            
            print(f"\nProcessing {len(routes)} routes...")
            
            results = []
            for i, route in enumerate(routes, 1):
                try:
                    origin = route.get('origin', '')
                    destination = route.get('destination', '')
                    mode_str = route.get('mode', 'driving')
                    
                    mode = TransportMode(mode_str.lower())
                    
                    print(f"\n[{i}/{len(routes)}] {origin} → {destination}")
                    
                    nav_result = self.nav_manager.navigate(
                        origin, destination, mode, open_browser=False, get_details=False
                    )
                    
                    results.append({
                        'origin': origin,
                        'destination': destination,
                        'mode': mode.value,
                        'distance': nav_result['route'].distance_text,
                        'duration': nav_result['route'].duration_text,
                        'maps_url': nav_result['maps_url']
                    })
                    
                    print(f"   ✓ Success: {nav_result['route'].distance_text}, {nav_result['route'].duration_text}")
                    
                except Exception as e:
                    print(f"   ❌ Failed: {e}")
                    results.append({
                        'origin': route.get('origin', ''),
                        'destination': route.get('destination', ''),
                        'error': str(e)
                    })
            
            # Save results
            output_file = f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['origin', 'destination', 'mode', 'distance', 'duration', 'maps_url', 'error']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
            
            print(f"\n💾 Results saved to {output_file}")
            
        except Exception as e:
            print(f"Error processing file: {e}")
    
    def main_menu(self):
        """Main application menu"""
        if not self.api_key:
            self.setup_api_key()
        
        self.api = GoogleMapsAPI(self.api_key)
        self.nav_manager = NavigationManager(self.api)
        
        while True:
            self.print_banner()
            
            print("\nMAIN MENU:")
            print("1. 🚗 Quick Navigation")
            print("2. 🔍 Search Places")
            print("3. 🗺️ Multi-Destination Trip")
            print("4. 📁 Batch Navigation (from CSV)")
            print("5. 📜 View History")
            print("6. 💾 Save History")
            print("7. ⚙️ Reconfigure API Key")
            print("8. 🚪 Exit")
            
            choice = input("\nSelect option (1-8): ").strip()
            
            if choice == "1":
                self.quick_navigation()
            elif choice == "2":
                self.search_places()
            elif choice == "3":
                self.multi_destination_trip()
            elif choice == "4":
                self.batch_navigation()
            elif choice == "5":
                self.nav_manager.show_history()
            elif choice == "6":
                self.nav_manager.save_history()
            elif choice == "7":
                self.setup_api_key()
                self.api = GoogleMapsAPI(self.api_key)
                self.nav_manager = NavigationManager(self.api)
            elif choice == "8":
                print("\nThank you for using Google Maps Navigation System!")
                break
            else:
                print("\nInvalid choice!")
            
            input("\nPress Enter to continue...")

def main():
    """Main entry point"""
    try:
        app = GoogleMapsNavigator()
        app.main_menu()
    except KeyboardInterrupt:
        print("\n\nProgram terminated by user.")
    except Exception as e:
        print(f"\nFatal error: {e}")
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
