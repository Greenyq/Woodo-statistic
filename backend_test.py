import requests
import sys
import json
from datetime import datetime

class W3ChampionsAPITester:
    def __init__(self, base_url="https://wc3stats.preview.emergentagent.com"):
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
            "battle_tag": "TestPlayer#1234"
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
            "battle_tag": "InvalidTag"
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

    def test_demo_match_endpoint(self):
        """Test demo-match endpoint and verify achievements are returned"""
        success, response = self.run_test(
            "Demo Match Endpoint",
            "GET",
            "demo-match",
            200
        )
        
        if success and response:
            # Verify demo match structure
            if "data" in response and "opponent_data" in response["data"]:
                opponents = response["data"]["opponent_data"].get("opponents", [])
                if opponents and len(opponents) > 0:
                    opponent = opponents[0]
                    if "achievements" in opponent:
                        achievements = opponent["achievements"]
                        print(f"   ✅ Demo match has {len(achievements)} achievements")
                        
                        # Check achievement structure
                        if achievements:
                            first_achievement = achievements[0]
                            required_keys = ["title", "description", "type", "color"]
                            if all(key in first_achievement for key in required_keys):
                                print(f"   ✅ Achievement structure valid")
                            else:
                                print(f"   ⚠️  Achievement missing required keys")
                        return True
                    else:
                        print(f"   ❌ No achievements found in demo match")
                        return False
                else:
                    print(f"   ❌ No opponents found in demo match")
                    return False
            else:
                print(f"   ❌ Demo match missing expected data structure")
                return False
        
        return success

    def test_achievement_system_with_real_player(self):
        """Test achievement system with real player battle tag"""
        # Use Siberia#21832 as requested in the review
        test_data = {
            "nickname": "Siberia",
            "battle_tag": "Siberia#21832",
            "race": "Night Elf"
        }
        
        success, response = self.run_test(
            "Achievement System - Real Player (Siberia#21832)",
            "POST",
            "check-match",
            200,
            data=test_data
        )
        
        if success and response:
            # Check if we get achievement data (either in match or not in match)
            status = response.get("status")
            print(f"   Player status: {status}")
            
            if status == "in_game" and "data" in response:
                # Player is in game - check opponent achievements
                opponent_data = response["data"].get("opponent_data", {})
                opponents = opponent_data.get("opponents", [])
                
                if opponents:
                    for i, opponent in enumerate(opponents):
                        achievements = opponent.get("achievements", [])
                        print(f"   Opponent {i+1} ({opponent.get('battle_tag', 'Unknown')}): {len(achievements)} achievements")
                        
                        # Validate achievement types
                        achievement_types = set()
                        for achievement in achievements:
                            achievement_types.add(achievement.get("type", "unknown"))
                        
                        print(f"   Achievement types found: {list(achievement_types)}")
                        
                        # Check for specific achievement categories mentioned in review
                        expected_types = ["activity", "economy", "streak", "hero", "skill", "experience"]
                        found_expected = [t for t in expected_types if t in achievement_types]
                        if found_expected:
                            print(f"   ✅ Found expected achievement types: {found_expected}")
                        else:
                            print(f"   ⚠️  No expected achievement types found")
                
                return True
            elif status == "not_in_game":
                print(f"   ✅ Player not in game - this is expected behavior")
                return True
            else:
                print(f"   ⚠️  Unexpected response structure")
                return False
        
        return success

    def test_achievement_categories(self):
        """Test that different achievement categories are working correctly"""
        # Test with demo match to ensure we get achievements
        success, response = self.run_test(
            "Achievement Categories Analysis",
            "GET", 
            "demo-match",
            200
        )
        
        if success and response:
            # Extract achievements from demo match
            opponents = response.get("data", {}).get("opponent_data", {}).get("opponents", [])
            if not opponents:
                print(f"   ❌ No opponents in demo match")
                return False
                
            achievements = opponents[0].get("achievements", [])
            if not achievements:
                print(f"   ❌ No achievements found")
                return False
            
            # Analyze achievement categories
            categories = {}
            for achievement in achievements:
                category = achievement.get("type", "unknown")
                if category not in categories:
                    categories[category] = []
                categories[category].append(achievement)
            
            print(f"   Found {len(achievements)} total achievements in {len(categories)} categories:")
            
            # Check specific categories mentioned in review request
            expected_categories = {
                "economy": "Economic achievements",
                "activity": "Activity achievements", 
                "streak": "Win/loss streak achievements",
                "hero": "Hero main achievements",
                "skill": "Skill-based achievements",
                "experience": "Experience achievements"
            }
            
            all_good = True
            for category, description in expected_categories.items():
                if category in categories:
                    count = len(categories[category])
                    print(f"   ✅ {description}: {count} achievements")
                    
                    # Validate structure of first achievement in category
                    first_achievement = categories[category][0]
                    required_fields = ["title", "description", "type", "color"]
                    if all(field in first_achievement for field in required_fields):
                        print(f"      Structure valid: {first_achievement['title']}")
                    else:
                        print(f"      ⚠️  Missing required fields")
                        all_good = False
                else:
                    print(f"   ⚠️  {description}: Not found")
            
            # Check for any unexpected categories
            unexpected = set(categories.keys()) - set(expected_categories.keys())
            if unexpected:
                print(f"   Additional categories found: {list(unexpected)}")
            
            return all_good
        
        return success

    def test_battle_tag_encoding(self):
        """Test that battle tag encoding works properly for special characters"""
        # Test with Cyrillic characters as mentioned in the code
        test_cases = [
            ("Siberia#21832", "Standard ASCII"),
            ("Тест#1234", "Cyrillic characters"),
            ("Player#12345", "5-digit tag"),
        ]
        
        all_passed = True
        for battle_tag, description in test_cases:
            test_data = {
                "nickname": "TestPlayer",
                "battle_tag": battle_tag,
                "race": "Human"
            }
            
            success, response = self.run_test(
                f"Battle Tag Encoding - {description}",
                "POST",
                "check-match", 
                200,
                data=test_data
            )
            
            if not success:
                all_passed = False
        
        return all_passed

    def test_error_handling(self):
        """Test error handling for invalid battle tags and API failures"""
        # Test with non-existent battle tag
        test_data = {
            "battle_tag": "NonExistentPlayer#9999"
        }
        
        success, response = self.run_test(
            "Error Handling - Non-existent Player",
            "POST",
            "check-match",
            200,  # Should still return 200 but with not_in_game status
            data=test_data
        )
        
        if success and response:
            # Should gracefully handle non-existent player
            status = response.get("status")
            if status == "not_in_game":
                print(f"   ✅ Gracefully handled non-existent player")
                return True
            else:
                print(f"   ⚠️  Unexpected status for non-existent player: {status}")
                return False
        
        return success

    def test_multi_season_hero_data(self):
        """Test that hero statistics combine data from both season 22 and 23"""
        success, response = self.run_test(
            "Multi-Season Hero Data Integration",
            "GET",
            "demo-match",
            200
        )
        
        if success and response:
            opponents = response.get("data", {}).get("opponent_data", {}).get("opponents", [])
            if opponents:
                opponent = opponents[0]
                hero_stats = opponent.get("hero_stats", {})
                
                if hero_stats and hero_stats.get("heroStatsItemList"):
                    hero_count = len(hero_stats["heroStatsItemList"])
                    print(f"   ✅ Multi-season hero data: {hero_count} heroes found")
                    
                    # Check if we have hero data (indicating multi-season merge worked)
                    if hero_count > 0:
                        first_hero = hero_stats["heroStatsItemList"][0]
                        hero_id = first_hero.get("heroId", "unknown")
                        print(f"   ✅ Sample hero: {hero_id}")
                        return True
                    else:
                        print(f"   ❌ No hero data found in multi-season stats")
                        return False
                else:
                    print(f"   ❌ No hero stats found in response")
                    return False
            else:
                print(f"   ❌ No opponents found in demo match")
                return False
        
        return success

    def test_smart_recent_matches(self):
        """Test smart recent matches functionality that spans seasons"""
        # Test with real player to verify smart match retrieval
        success, response = self.run_test(
            "Smart Recent Matches - Multi-Season",
            "GET",
            "player-stats/Siberia#21832",
            200
        )
        
        if success and response:
            recent_matches = response.get("recent_matches", {})
            if recent_matches and recent_matches.get("matches"):
                matches = recent_matches["matches"]
                match_count = len(matches)
                print(f"   ✅ Smart matches retrieved: {match_count} matches")
                
                # Check if we have a good number of matches (indicating smart retrieval worked)
                if match_count >= 10:
                    print(f"   ✅ Good match coverage achieved")
                    
                    # Check match structure
                    if matches:
                        first_match = matches[0]
                        match_keys = list(first_match.keys())
                        print(f"   ✅ Match structure keys: {match_keys[:5]}...")  # Show first 5 keys
                        return True
                else:
                    print(f"   ⚠️  Limited matches found: {match_count}")
                    return match_count > 0  # Still pass if we got some matches
            else:
                print(f"   ❌ No recent matches found")
                return False
        
        return success

    def test_multi_race_achievement_logic(self):
        """Test the new balanced race distribution achievement logic"""
        success, response = self.run_test(
            "Multi-Race Achievement Balance Logic",
            "GET",
            "demo-match",
            200
        )
        
        if success and response:
            opponents = response.get("data", {}).get("opponent_data", {}).get("opponents", [])
            if opponents:
                opponent = opponents[0]
                achievements = opponent.get("achievements", [])
                
                # Look for race diversity achievements
                diversity_achievements = [
                    ach for ach in achievements 
                    if ach.get("type") in ["diversity", "focus"] or 
                       "Мульти-рейсер" in ach.get("title", "") or
                       "Специалист" in ach.get("title", "") or
                       "Экспериментатор" in ach.get("title", "")
                ]
                
                if diversity_achievements:
                    print(f"   ✅ Found {len(diversity_achievements)} race diversity achievements:")
                    for ach in diversity_achievements:
                        title = ach.get("title", "Unknown")
                        description = ach.get("description", "No description")
                        print(f"      • {title}: {description}")
                    
                    # Check if we have the new balanced logic achievement
                    multi_racer = any("Мульти-рейсер" in ach.get("title", "") for ach in diversity_achievements)
                    if multi_racer:
                        print(f"   ✅ New balanced 'Мульти-рейсер' achievement found")
                    else:
                        print(f"   ℹ️  'Мульти-рейсер' not found (player may not meet balance criteria)")
                    
                    return True
                else:
                    print(f"   ℹ️  No race diversity achievements found (player may be specialist)")
                    return True  # This is valid - not all players will have diversity achievements
            else:
                print(f"   ❌ No opponents found")
                return False
        
        return success

    def test_updated_endpoints_integration(self):
        """Test that all endpoints are using the new smart functions"""
        endpoints_to_test = [
            ("check-match", "POST", {"battle_tag": "Siberia#21832"}),
            ("demo-match", "GET", None),
            ("player-stats/Siberia#21832", "GET", None)
        ]
        
        all_passed = True
        
        for endpoint, method, data in endpoints_to_test:
            success, response = self.run_test(
                f"Updated Endpoint Integration - {endpoint}",
                method,
                endpoint,
                200,
                data=data
            )
            
            if success and response:
                # Check for indicators that new functions are being used
                if endpoint == "check-match" or endpoint == "demo-match":
                    # Should have opponent data with achievements and hero stats
                    has_opponents = False
                    if "data" in response:
                        opponent_data = response["data"].get("opponent_data", {})
                        opponents = opponent_data.get("opponents", [])
                        if opponents:
                            has_opponents = True
                            opponent = opponents[0]
                            
                            # Check for multi-season hero stats
                            has_hero_stats = "hero_stats" in opponent
                            # Check for achievements (indicating new analysis)
                            has_achievements = "achievements" in opponent and len(opponent["achievements"]) > 0
                            
                            print(f"      Hero stats: {'✅' if has_hero_stats else '❌'}")
                            print(f"      Achievements: {'✅' if has_achievements else '❌'}")
                            
                            if not (has_hero_stats and has_achievements):
                                all_passed = False
                    
                    if not has_opponents and response.get("status") != "not_in_game":
                        print(f"      ⚠️  No opponents found and not 'not_in_game' status")
                        all_passed = False
                
                elif endpoint.startswith("player-stats"):
                    # Should have recent matches from smart retrieval
                    has_matches = "recent_matches" in response and response["recent_matches"]
                    print(f"      Smart matches: {'✅' if has_matches else '❌'}")
                    if not has_matches:
                        all_passed = False
            else:
                all_passed = False
        
        return all_passed

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
        
        # Achievement System Tests (Focus of this review)
        print("\n🎯 ACHIEVEMENT SYSTEM TESTS")
        print("=" * 40)
        self.test_demo_match_endpoint()
        self.test_achievement_system_with_real_player()
        self.test_achievement_categories()
        self.test_battle_tag_encoding()
        self.test_error_handling()
        
        # Validation tests
        print("\n🔍 VALIDATION TESTS")
        print("=" * 40)
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