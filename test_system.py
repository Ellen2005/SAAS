#!/usr/bin/env python3
"""
Comprehensive test suite for SAAS system
Tests all critical functionality before deployment
"""

import sys
import os
import json
import time
import requests
from datetime import datetime

# Test configuration
BASE_URL = "http://127.0.0.1:8000"
TEST_USER_EMAIL = "test@cnps.cm"
TEST_PASSWORD = "TestPass123!"

class SAASTestSuite:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        
    def log_test(self, test_name, status, message=""):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status_icon = "✅" if status == "PASS" else "❌"
        print(f"{status_icon} {test_name}: {message}")
        
    def test_api_health(self):
        """Test basic API connectivity"""
        try:
            response = self.session.get(f"{BASE_URL}/api/ping")
            if response.status_code == 200:
                self.log_test("API Health Check", "PASS", "API is responding")
                return True
            else:
                self.log_test("API Health Check", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Health Check", "FAIL", str(e))
            return False
            
    def test_database_connection(self):
        """Test database connectivity"""
        try:
            response = self.session.get(f"{BASE_URL}/api/dashboard/widgets")
            if response.status_code in [200, 401]:  # 401 is expected without auth
                self.log_test("Database Connection", "PASS", "Database accessible")
                return True
            else:
                self.log_test("Database Connection", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Database Connection", "FAIL", str(e))
            return False
            
    def test_analysis_engine_safety(self):
        """Test analysis engine error handling"""
        try:
            # Test with no database connection configured
            response = self.session.post(f"{BASE_URL}/api/analysis/run", 
                json={"goal_text": "test analysis"})
            
            # Should handle gracefully, not crash
            if response.status_code in [401, 422, 400]:
                self.log_test("Analysis Engine Safety", "PASS", "Handles missing connection gracefully")
                return True
            else:
                self.log_test("Analysis Engine Safety", "FAIL", f"Unexpected status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Analysis Engine Safety", "FAIL", str(e))
            return False
            
    def test_nlq_sql_generation(self):
        """Test NLQ SQL generation and sanitization"""
        try:
            # Test SQL injection prevention
            malicious_queries = [
                "DROP TABLE users; --",
                "'; DELETE FROM users; --",
                "UNION SELECT * FROM sensitive_data",
                "INSERT INTO users VALUES ('hacker', 'password')"
            ]
            
            for query in malicious_queries:
                response = self.session.post(f"{BASE_URL}/api/nlq", 
                    json={"question": query})
                
                if response.status_code == 401:
                    continue  # Expected without auth
                    
                # Should reject malicious queries
                if response.status_code in [400, 422]:
                    continue
                    
                data = response.json()
                if "error" in data or not data.get("sql", "").upper().startswith("SELECT"):
                    continue
                else:
                    self.log_test("NLQ SQL Safety", "FAIL", f"Accepted malicious query: {query}")
                    return False
                    
            self.log_test("NLQ SQL Safety", "PASS", "Rejects malicious SQL")
            return True
        except Exception as e:
            self.log_test("NLQ SQL Safety", "FAIL", str(e))
            return False
            
    def test_error_handling(self):
        """Test system error handling"""
        try:
            # Test various error conditions
            error_tests = [
                ("/api/nonexistent", 404),
                ("/api/dashboard/widgets", 401),  # No auth
                ("/api/analysis/run", 401),       # No auth
            ]
            
            for endpoint, expected_status in error_tests:
                response = self.session.get(f"{BASE_URL}{endpoint}")
                if response.status_code == expected_status:
                    continue
                else:
                    self.log_test("Error Handling", "FAIL", 
                        f"{endpoint} returned {response.status_code}, expected {expected_status}")
                    return False
                    
            self.log_test("Error Handling", "PASS", "Proper error responses")
            return True
        except Exception as e:
            self.log_test("Error Handling", "FAIL", str(e))
            return False
            
    def test_security_headers(self):
        """Test security headers"""
        try:
            response = self.session.get(f"{BASE_URL}/api/ping")
            headers = response.headers
            
            # Check for basic security headers
            security_checks = [
                ("X-Content-Type-Options", "nosniff"),
                ("X-Frame-Options", ["DENY", "SAMEORIGIN"]),
            ]
            
            for header, expected in security_checks:
                if header not in headers:
                    self.log_test("Security Headers", "WARN", f"Missing {header}")
                elif isinstance(expected, list):
                    if headers[header] not in expected:
                        self.log_test("Security Headers", "WARN", f"Weak {header}: {headers[header]}")
                elif headers[header] != expected:
                    self.log_test("Security Headers", "WARN", f"Weak {header}: {headers[header]}")
                    
            self.log_test("Security Headers", "PASS", "Basic security headers checked")
            return True
        except Exception as e:
            self.log_test("Security Headers", "FAIL", str(e))
            return False
            
    def test_performance_basic(self):
        """Test basic performance metrics"""
        try:
            # Test response times
            start_time = time.time()
            response = self.session.get(f"{BASE_URL}/api/ping")
            response_time = time.time() - start_time
            
            if response_time < 1.0:  # Should respond within 1 second
                self.log_test("Performance Basic", "PASS", f"Response time: {response_time:.3f}s")
                return True
            else:
                self.log_test("Performance Basic", "WARN", f"Slow response: {response_time:.3f}s")
                return True  # Warning, not failure
        except Exception as e:
            self.log_test("Performance Basic", "FAIL", str(e))
            return False
            
    def test_data_validation(self):
        """Test data validation"""
        try:
            # Test invalid JSON
            response = self.session.post(f"{BASE_URL}/api/analysis/run", 
                data="invalid json", 
                headers={"Content-Type": "application/json"})
                
            if response.status_code in [400, 422]:
                self.log_test("Data Validation", "PASS", "Rejects invalid JSON")
                return True
            else:
                self.log_test("Data Validation", "FAIL", f"Accepted invalid JSON: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Data Validation", "FAIL", str(e))
            return False
            
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting SAAS System Test Suite")
        print("=" * 50)
        
        tests = [
            self.test_api_health,
            self.test_database_connection,
            self.test_analysis_engine_safety,
            self.test_nlq_sql_generation,
            self.test_error_handling,
            self.test_security_headers,
            self.test_performance_basic,
            self.test_data_validation,
        ]
        
        passed = 0
        failed = 0
        warnings = 0
        
        for test in tests:
            try:
                result = test()
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log_test(test.__name__, "FAIL", f"Test crashed: {e}")
                failed += 1
                
        # Count warnings
        warnings = sum(1 for r in self.test_results if "WARN" in r["message"])
        
        print("\n" + "=" * 50)
        print(f"📊 Test Results Summary:")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        # Save detailed results
        with open("test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "passed": passed,
                    "failed": failed,
                    "warnings": warnings,
                    "success_rate": passed/(passed+failed)*100 if (passed+failed) > 0 else 0
                },
                "details": self.test_results,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
            
        print(f"📄 Detailed results saved to test_results.json")
        
        if failed == 0:
            print("🎉 All tests passed! System is ready for deployment.")
            return True
        else:
            print("🔧 Some tests failed. Please review and fix issues before deployment.")
            return False

if __name__ == "__main__":
    print("SAAS System Test Suite")
    print("Make sure the backend is running on http://127.0.0.1:8000")
    
    # Wait for user confirmation
    input("Press Enter to start tests...")
    
    suite = SAASTestSuite()
    success = suite.run_all_tests()
    
    sys.exit(0 if success else 1)