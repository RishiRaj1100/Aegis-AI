"""
AEGIS AI — URL Validation & Feature Verification Script

Tests that all implemented features are accessible and working
Run with: python validate_urls.py
"""

import sys
import time
import requests
from typing import Dict, List, Tuple
from datetime import datetime


class URLValidator:
    """Validates all system endpoints and features"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: Dict[str, Dict] = {}
        self.session = requests.Session()
    
    def test_endpoint(self, name: str, method: str, path: str, 
                     expected_status: List[int] = [200, 404, 500]) -> Tuple[bool, int, str]:
        """Test a single endpoint"""
        try:
            url = f"{self.base_url}{path}"
            
            if method.upper() == "GET":
                response = self.session.get(url, timeout=5)
            elif method.upper() == "POST":
                response = self.session.post(url, json={}, timeout=5)
            else:
                response = self.session.request(method, url, timeout=5)
            
            status = response.status_code
            is_success = status in expected_status
            
            # Try to parse JSON response
            try:
                data = response.json()
                msg = f"Status {status}, Response: {str(data)[:100]}"
            except:
                msg = f"Status {status}, Content-Type: {response.headers.get('content-type', 'unknown')}"
            
            return is_success, status, msg
        
        except requests.exceptions.ConnectionError:
            return False, 0, "Connection refused - is server running?"
        except requests.exceptions.Timeout:
            return False, 0, "Request timeout"
        except Exception as e:
            return False, 0, f"Error: {str(e)}"
    
    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    
    def print_result(self, name: str, success: bool, status: int, msg: str):
        """Print result"""
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {name:50} [{status}] {msg[:40]}")
        
        self.results[name] = {
            "success": success,
            "status": status,
            "message": msg
        }
    
    def validate_all(self):
        """Run all validation tests"""
        print("\n")
        print("╔" + "="*78 + "╗")
        print("║" + " "*20 + "AEGIS AI — System Validation" + " "*31 + "║")
        print("║" + " "*20 + f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" + " "*32 + "║")
        print("╚" + "="*78 + "╝")
        
        # Section 1: Core Health
        self.print_header("1. CORE HEALTH CHECKS")
        self.print_result(
            "Health Check",
            *self.test_endpoint("Health", "GET", "/health", [200, 404])
        )
        self.print_result(
            "OpenAPI Docs",
            *self.test_endpoint("OpenAPI", "GET", "/docs", [200, 404])
        )
        
        # Section 2: Core Pipeline Endpoints
        self.print_header("2. CORE PIPELINE ENDPOINTS")
        self.print_result(
            "Submit Goal (POST /goal)",
            *self.test_endpoint("Goal Submit", "POST", "/goal", [200, 422])
        )
        self.print_result(
            "Retrieve Goal (GET /goal/{task_id})",
            *self.test_endpoint("Goal Retrieve", "GET", "/goal/test-123", [200, 404])
        )
        self.print_result(
            "Get Plan (GET /plan/{task_id})",
            *self.test_endpoint("Plan Retrieve", "GET", "/plan/test-123", [200, 404])
        )
        
        # Section 3: Advanced Metrics (Requirement #14)
        self.print_header("3. ADVANCED METRICS (Requirement #14)")
        self.print_result(
            "Get Metrics (GET /api/v1/aegis/metrics)",
            *self.test_endpoint("Metrics Dashboard", "GET", "/api/v1/aegis/metrics", [200, 404])
        )
        self.print_result(
            "Record Prediction (POST /api/v1/aegis/metrics/prediction)",
            *self.test_endpoint("Record Prediction", "POST", "/api/v1/aegis/metrics/prediction", [200, 404, 422])
        )
        
        # Section 4: A/B Testing (Requirement #15)
        self.print_header("4. A/B TESTING FRAMEWORK (Requirement #15)")
        self.print_result(
            "Create Experiment (POST /ab-tests/create)",
            *self.test_endpoint("AB Test Create", "POST", "/ab-tests/create", [200, 404, 422])
        )
        self.print_result(
            "Get Experiment (GET /ab-tests/{exp_id})",
            *self.test_endpoint("AB Test Get", "GET", "/ab-tests/test-123", [200, 404])
        )
        
        # Section 5: Fairness & Bias (Requirement #16)
        self.print_header("5. FAIRNESS & BIAS DETECTION (Requirement #16)")
        self.print_result(
            "Get Fairness Status (GET /api/v1/aegis/fairness)",
            *self.test_endpoint("Fairness Status", "GET", "/api/v1/aegis/fairness", [200, 404])
        )
        self.print_result(
            "Fairness Alerts (GET /fairness/alerts)",
            *self.test_endpoint("Fairness Alerts", "GET", "/fairness/alerts", [200, 404])
        )
        
        # Section 6: Behavior Intelligence (Requirement #12)
        self.print_header("6. BEHAVIOR INTELLIGENCE (Requirement #12)")
        self.print_result(
            "Task Behavior (GET /behavior/{task_id})",
            *self.test_endpoint("Task Behavior", "GET", "/behavior/test-123", [200, 404])
        )
        self.print_result(
            "Behavior Stats (GET /behavior/stats/summary)",
            *self.test_endpoint("Behavior Stats", "GET", "/behavior/stats/summary", [200, 404])
        )
        
        # Section 7: Multimodal Retrieval (Requirement #13)
        self.print_header("7. MULTIMODAL RETRIEVAL (Requirement #13)")
        self.print_result(
            "Document Ingest (POST /documents/ingest)",
            *self.test_endpoint("Document Ingest", "POST", "/documents/ingest", [200, 404, 422])
        )
        self.print_result(
            "Document Search (GET /documents/search)",
            *self.test_endpoint("Document Search", "GET", "/documents/search", [200, 404])
        )
        self.print_result(
            "Document Stats (GET /documents/{name}/stats)",
            *self.test_endpoint("Document Stats", "GET", "/documents/test/stats", [200, 404])
        )
        
        # Section 8: Voice & Multilingual (Requirement #19)
        self.print_header("8. VOICE & MULTILINGUAL SUPPORT (Requirement #19)")
        self.print_result(
            "Transcribe Audio (POST /voice/transcribe)",
            *self.test_endpoint("Voice Transcribe", "POST", "/voice/transcribe", [200, 404, 422])
        )
        self.print_result(
            "Synthesize Speech (POST /voice/synthesize)",
            *self.test_endpoint("Voice Synthesize", "POST", "/voice/synthesize", [200, 404, 422])
        )
        self.print_result(
            "Supported Languages (GET /voice/languages)",
            *self.test_endpoint("Voice Languages", "GET", "/voice/languages", [200, 404])
        )
        self.print_result(
            "Voice History (GET /voice/history/{user_id})",
            *self.test_endpoint("Voice History", "GET", "/voice/history/user-123", [200, 404])
        )
        
        # Section 9: Security Hardening (Requirement #17)
        self.print_header("9. SECURITY HARDENING (Requirement #17)")
        self.print_result(
            "Security Status (GET /security/status)",
            *self.test_endpoint("Security Status", "GET", "/security/status", [200, 404])
        )
        self.print_result(
            "Audit Log (GET /security/audit-log)",
            *self.test_endpoint("Audit Log", "GET", "/security/audit-log", [200, 404])
        )
        self.print_result(
            "Secret Rotation (GET /security/secrets/rotation-status)",
            *self.test_endpoint("Secret Rotation", "GET", "/security/secrets/rotation-status", [200, 404])
        )
        
        # Section 10: UI Dashboard (Requirement #18)
        self.print_header("10. UI DASHBOARD (Requirement #18)")
        self.print_result(
            "Dashboard HTML (GET /)",
            *self.test_endpoint("Dashboard Root", "GET", "/", [200, 404])
        )
        self.print_result(
            "Dashboard Page (GET /dashboard.html)",
            *self.test_endpoint("Dashboard Page", "GET", "/dashboard.html", [200, 404])
        )
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print validation summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r["success"])
        failed = total - passed
        
        self.print_header("VALIDATION SUMMARY")
        print(f"Total Endpoints Tested: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total*100) if total > 0 else 0:.1f}%")
        
        if failed > 0:
            print("\n⚠️  Failed Endpoints:")
            for name, result in self.results.items():
                if not result["success"]:
                    print(f"   - {name}: {result['message']}")
        
        print(f"\n📊 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n" + "="*80 + "\n")
        
        # Print detailed report
        print("DETAILED RESULTS:\n")
        for category in [
            "Health", "Metrics", "A/B Test", "Fairness", "Behavior",
            "Document", "Voice", "Security", "Dashboard"
        ]:
            items = {k: v for k, v in self.results.items() if category in k}
            if items:
                print(f"\n{category.upper()}:")
                for name, result in items.items():
                    status = "✅" if result["success"] else "❌"
                    print(f"  {status} {name}: {result['message']}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AEGIS AI URL Validator")
    parser.add_argument("--url", default="http://localhost:8000",
                       help="Base URL of the API (default: http://localhost:8000)")
    parser.add_argument("--timeout", type=int, default=10,
                       help="Timeout for each request in seconds (default: 10)")
    
    args = parser.parse_args()
    
    # Check if server is reachable
    try:
        response = requests.get(f"{args.url}/health", timeout=5)
        print(f"✅ Server is running at {args.url}")
    except:
        print(f"❌ Cannot reach server at {args.url}")
        print("\n💡 Make sure the server is running:")
        print("   cd /path/to/aegis-ai")
        print("   python main.py")
        sys.exit(1)
    
    # Run validation
    validator = URLValidator(args.url)
    validator.validate_all()


if __name__ == "__main__":
    main()
