import requests
import sys
import json
from datetime import datetime

class W3ChampionsAPITester:
    def __init__(self, base_url="https://matchscouter.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test_name": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"\n{status} - {name}")
        if details:
            print(f"   Details: {details}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json()
                    details = f"Status: {response.status_code}, Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Non-dict response'}"
                except:
                    details = f"Status: {response.status_code}, Response: {response.text[:100]}..."
            else:
                details = f"Expected {expected_status}, got {response.status_code}. Response: {response.text[:200]}..."

            self.log_test(name, success, details)
            return success, response.json() if success and response.text else {}

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.log_test(name, False, error_msg)
            return False, {}

    def test_api_root(self):
        """Test API root endpoint"""
        return self.run_test(
            "API Root",
            "GET",
            "",
            200
        )

    def test_check_match_valid_input(self):
        """Test check-match with valid player input"""
        test_data = {
            "nickname": "TestPlayer",
            "battle_tag": "TestPlayer#1234",
            "race": "Human"
        }
        return self.run_test(
            "Check Match - Valid Input",
            "POST",
            "check-match",
            200,
            data=test_data
        )

    def test_check_match_invalid_battle_tag(self):
        """Test check-match with invalid battle tag format"""
        test_data = {
            "nickname": "TestPlayer",
            "battle_tag": "InvalidTag",
            "race": "Human"
        }
        return self.run_test(
            "Check Match - Invalid Battle Tag",
            "POST",
            "check-match",
            422,  # Validation error
            data=test_data
        )

    def test_check_match_invalid_race(self):
        """Test check-match with invalid race"""
        test_data = {
            "nickname": "TestPlayer",
            "battle_tag": "TestPlayer#1234",
            "race": "InvalidRace"
        }
        return self.run_test(
            "Check Match - Invalid Race",
            "POST",
            "check-match",
            422,  # Validation error
            data=test_data
        )

    def test_check_match_missing_fields(self):
        """Test check-match with missing required fields"""
        test_data = {
            "nickname": "TestPlayer"
            # Missing battle_tag and race
        }
        return self.run_test(
            "Check Match - Missing Fields",
            "POST",
            "check-match",
            422,  # Validation error
            data=test_data
        )

    def test_player_stats_endpoint(self):
        """Test player-stats endpoint"""
        battle_tag = "TestPlayer#1234"
        return self.run_test(
            "Player Stats",
            "GET",
            f"player-stats/{battle_tag}",
            200
        )

    def test_match_history_endpoint(self):
        """Test match-history endpoint"""
        return self.run_test(
            "Match History",
            "GET",
            "match-history",
            200
        )

    def test_race_validation(self):
        """Test all valid races"""
        valid_races = ["Human", "Orc", "Night Elf", "Undead", "Random"]
        all_passed = True
        
        for race in valid_races:
            test_data = {
                "nickname": "TestPlayer",
                "battle_tag": "TestPlayer#1234",
                "race": race
            }
            success, _ = self.run_test(
                f"Race Validation - {race}",
                "POST",
                "check-match",
                200,
                data=test_data
            )
            if not success:
                all_passed = False
        
        return all_passed

    def test_battle_tag_formats(self):
        """Test various battle tag formats"""
        test_cases = [
            ("ValidTag#1234", True, "Valid 4-digit"),
            ("ValidTag#12345", True, "Valid 5-digit"),
            ("Player123#9999", True, "Valid with numbers"),
            ("InvalidTag", False, "No # symbol"),
            ("Invalid#123", False, "3 digits"),
            ("Invalid#123456", False, "6 digits"),
            ("Invalid#Tag", False, "Non-numeric after #"),
            ("", False, "Empty string"),
            ("Player#", False, "No digits after #")
        ]
        
        all_passed = True
        for battle_tag, should_pass, description in test_cases:
            test_data = {
                "nickname": "TestPlayer",
                "battle_tag": battle_tag,
                "race": "Human"
            }
            expected_status = 200 if should_pass else 422
            success, _ = self.run_test(
                f"Battle Tag Format - {description}",
                "POST",
                "check-match",
                expected_status,
                data=test_data
            )
            if not success:
                all_passed = False
        
        return all_passed

    def test_w3champions_integration(self):
        """Test integration with real W3Champions API"""
        # Test with a known player (this might not be in game, but should return valid response)
        test_data = {
            "nickname": "TestPlayer",
            "battle_tag": "Dantas#1378",  # Example from the API docs
            "race": "Human"
        }
        success, response = self.run_test(
            "W3Champions Integration",
            "POST",
            "check-match",
            200,
            data=test_data
        )
        
        if success and response:
            # Check if response has expected structure
            expected_keys = ["status", "message", "data"]
            has_structure = all(key in response for key in expected_keys)
            if has_structure:
                print(f"   ✅ Response structure valid: {response.get('status')}")
            else:
                print(f"   ⚠️  Response missing expected keys: {list(response.keys())}")
        
        return success

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting W3Champions Match Scout Backend Tests")
        print(f"   Base URL: {self.base_url}")
        print(f"   API URL: {self.api_url}")
        print("=" * 60)

        # Basic API tests
        self.test_api_root()
        
        # Core functionality tests
        self.test_check_match_valid_input()
        self.test_player_stats_endpoint()
        self.test_match_history_endpoint()
        
        # Validation tests
        self.test_check_match_invalid_battle_tag()
        self.test_check_match_invalid_race()
        self.test_check_match_missing_fields()
        
        # Comprehensive validation tests
        self.test_race_validation()
        self.test_battle_tag_formats()
        
        # Integration test
        self.test_w3champions_integration()

        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Show failed tests
        failed_tests = [test for test in self.test_results if not test['success']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"   • {test['test_name']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = W3ChampionsAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump({
            'summary': {
                'tests_run': tester.tests_run,
                'tests_passed': tester.tests_passed,
                'success_rate': (tester.tests_passed/tester.tests_run)*100 if tester.tests_run > 0 else 0,
                'timestamp': datetime.now().isoformat()
            },
            'test_results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())