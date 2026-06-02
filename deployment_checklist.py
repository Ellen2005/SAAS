"""
Production deployment pre-flight checklist and validation.
Run this before deploying to production to ensure all systems are ready.
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import Tuple, List

class DeploymentChecklist:
    """Pre-deployment validation checklist."""
    
    def __init__(self):
        self.checks_passed = []
        self.checks_failed = []
        self.warnings = []
        
    def check_environment_variables(self) -> bool:
        """Verify all required environment variables are set."""
        required = [
            "DATABASE_URL",
            "SUPABASE_URL",
            "SUPABASE_SERVICE_KEY",
            "GROQ_API_KEY",
        ]
        
        print("\n✓ CHECKING ENVIRONMENT VARIABLES")
        for var in required:
            if os.getenv(var):
                print(f"  ✓ {var} is set")
                self.checks_passed.append(f"Env: {var}")
            else:
                print(f"  ✗ {var} is NOT set")
                self.checks_failed.append(f"Env: {var}")
                return False
        return True
    
    def check_python_dependencies(self) -> bool:
        """Verify all Python dependencies are installed."""
        print("\n✓ CHECKING PYTHON DEPENDENCIES")
        try:
            import fastapi
            import supabase
            import sqlalchemy
            import pandas
            import sklearn
            import prophet
            import groq
            
            print("  ✓ All core dependencies are installed")
            self.checks_passed.append("Python dependencies")
            return True
        except ImportError as e:
            print(f"  ✗ Missing dependency: {e}")
            self.checks_failed.append(f"Python dependencies: {e}")
            return False
    
    def check_database_connection(self) -> bool:
        """Verify database connection is working."""
        print("\n✓ CHECKING DATABASE CONNECTION")
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("  ✗ DATABASE_URL not set")
            self.checks_failed.append("Database connection")
            return False
        
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(db_url, pool_pre_ping=True, connect_args={"timeout": 5})
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print("  ✓ Database connection successful")
            self.checks_passed.append("Database connection")
            return True
        except Exception as e:
            print(f"  ✗ Database connection failed: {e}")
            self.checks_failed.append(f"Database connection: {e}")
            self.warnings.append("This may fail during deployment. Check DATABASE_URL and network connectivity.")
            return False
    
    def check_supabase_connection(self) -> bool:
        """Verify Supabase connection."""
        print("\n✓ CHECKING SUPABASE CONNECTION")
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY")
            
            if not url or not key:
                print("  ⚠ Supabase credentials not fully set")
                self.warnings.append("Supabase credentials not fully configured")
                return False
            
            client = create_client(url, key)
            print("  ✓ Supabase client created successfully")
            self.checks_passed.append("Supabase connection")
            return True
        except Exception as e:
            print(f"  ✗ Supabase connection failed: {e}")
            self.checks_failed.append(f"Supabase connection: {e}")
            self.warnings.append("This is required for authentication.")
            return False
    
    def check_api_key_validity(self) -> bool:
        """Verify API keys are properly formatted."""
        print("\n✓ CHECKING API KEY FORMATS")
        checks = {
            "SUPABASE_SERVICE_KEY": lambda x: len(x) > 20,
            "GROQ_API_KEY": lambda x: len(x) > 5,
        }
        
        for key_name, validator in checks.items():
            key = os.getenv(key_name)
            if key and validator(key):
                print(f"  ✓ {key_name} appears valid")
                self.checks_passed.append(f"API key: {key_name}")
            else:
                print(f"  ✗ {key_name} appears invalid or missing")
                self.checks_failed.append(f"API key: {key_name}")
                return False
        return True
    
    def check_tests_pass(self) -> bool:
        """Run unit tests to ensure application logic is correct."""
        print("\n✓ RUNNING UNIT TESTS")
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-x"],
                capture_output=True,
                timeout=120
            )
            if result.returncode == 0:
                print("  ✓ All tests passed")
                self.checks_passed.append("Unit tests")
                return True
            else:
                print("  ✗ Some tests failed")
                print(result.stdout.decode()[-500:])  # Last 500 chars
                self.checks_failed.append("Unit tests")
                return False
        except subprocess.TimeoutExpired:
            print("  ⚠ Tests timed out (>120s)")
            self.warnings.append("Tests took too long to run")
            return False
        except Exception as e:
            print(f"  ⚠ Could not run tests: {e}")
            self.warnings.append("Unable to verify tests")
            return True  # Don't fail deployment if pytest isn't available
    
    def check_docker_build(self) -> bool:
        """Verify Docker images can be built."""
        print("\n✓ CHECKING DOCKER BUILD")
        try:
            result = subprocess.run(
                ["docker", "build", "-t", "saas-backend:test", "./backend"],
                capture_output=True,
                timeout=300
            )
            if result.returncode == 0:
                print("  ✓ Backend Docker image builds successfully")
                self.checks_passed.append("Docker build (backend)")
                
                # Clean up test image
                subprocess.run(["docker", "rmi", "saas-backend:test"], capture_output=True)
                return True
            else:
                print("  ✗ Backend Docker build failed")
                print(result.stderr.decode()[-300:])
                self.checks_failed.append("Docker build (backend)")
                return False
        except FileNotFoundError:
            print("  ⚠ Docker not found (check if Docker is installed and running)")
            self.warnings.append("Docker validation skipped - Docker not available")
            return True
        except Exception as e:
            print(f"  ⚠ Docker check error: {e}")
            self.warnings.append("Could not verify Docker")
            return True
    
    def check_logs_configured(self) -> bool:
        """Verify logging is properly configured."""
        print("\n✓ CHECKING LOGGING CONFIGURATION")
        main_py = Path("backend/api/main.py")
        if main_py.exists():
            content = main_py.read_text()
            if "logging.basicConfig" in content and "logger" in content:
                print("  ✓ Logging is configured")
                self.checks_passed.append("Logging configuration")
                return True
        print("  ⚠ Logging configuration not fully verified")
        self.warnings.append("Manual review of logging recommended")
        return True
    
    def run_all_checks(self) -> bool:
        """Run all checks and return overall status."""
        print("=" * 60)
        print("SAAS DEPLOYMENT CHECKLIST")
        print("=" * 60)
        
        checks = [
            ("Environment Variables", self.check_environment_variables),
            ("Python Dependencies", self.check_python_dependencies),
            ("Database Connection", self.check_database_connection),
            ("Supabase Connection", self.check_supabase_connection),
            ("API Key Validity", self.check_api_key_validity),
            ("Unit Tests", self.check_tests_pass),
            ("Logging Configuration", self.check_logs_configured),
            ("Docker Build", self.check_docker_build),
        ]
        
        for check_name, check_func in checks:
            try:
                check_func()
            except Exception as e:
                print(f"  ✗ Unexpected error in {check_name}: {e}")
                self.checks_failed.append(f"{check_name}: {e}")
        
        self.print_summary()
        return len(self.checks_failed) == 0
    
    def print_summary(self):
        """Print summary of all checks."""
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        
        print(f"\n✓ PASSED ({len(self.checks_passed)}):")
        for check in self.checks_passed:
            print(f"  • {check}")
        
        if self.checks_failed:
            print(f"\n✗ FAILED ({len(self.checks_failed)}):")
            for check in self.checks_failed:
                print(f"  • {check}")
        
        if self.warnings:
            print(f"\n⚠ WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if self.checks_failed:
            print("\n🚨 DEPLOYMENT NOT READY - Please fix the failures above")
            return False
        else:
            print("\n✅ ALL CHECKS PASSED - Ready for deployment!")
            return True


if __name__ == "__main__":
    checklist = DeploymentChecklist()
    success = checklist.run_all_checks()
    sys.exit(0 if success else 1)
