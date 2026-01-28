#!/usr/bin/env python3
"""
Test script to validate the enhanced office action extraction functionality.
This script tests the new fields without breaking existing functionality.
"""

import sys
import os
sys.path.append('backend')

from app.models.office_action import OfficeActionExtractedData, OfficeActionHeader
from app.services.report_generator import ReportGenerator
import json

def test_enhanced_models():
    """Test that the enhanced models work with both old and new data."""
    print("Testing enhanced Pydantic models...")
    
    # Test 1: Existing data structure (should still work)
    old_data = {
        "header": {
            "application_number": "16/123,456",
            "office_action_date": "2024-01-15",
            "office_action_type": "Non-Final",
            "examiner_name": "John Smith",
            "art_unit": "2100"
        },
        "claims_status": [
            {"claim_number": "1", "status": "Rejected", "dependency_type": "Independent"}
        ],
        "rejections": [],
        "objections": [],
        "other_statements": []
    }
    
    try:
        oa_old = OfficeActionExtractedData(**old_data)
        print("✓ Old data structure works correctly")
    except Exception as e:
        print(f"✗ Old data structure failed: {e}")
        return False
    
    # Test 2: Enhanced data structure with new fields
    enhanced_data = {
        "header": {
            "application_number": "16/123,456",
            "filing_date": "2023-06-15",
            "office_action_date": "2024-01-15",
            "office_action_type": "Non-Final",
            "examiner_name": "John Smith",
            "art_unit": "2100",
            "attorney_docket_number": "ABC-001",
            "confirmation_number": "1234",
            "response_deadline": "2024-04-15",
            "first_named_inventor": "Jane Doe",
            "applicant_name": "Tech Corp Inc.",
            "title_of_invention": "Advanced Widget System",
            "customer_number": "12345",
            "examiner_phone": "(571) 272-1000",
            "examiner_email": "john.smith@uspto.gov",
            "examiner_type": "Primary Examiner"
        },
        "claims_status": [
            {"claim_number": "1", "status": "Rejected", "dependency_type": "Independent"},
            {"claim_number": "2", "status": "Rejected", "dependency_type": "Dependent", "parent_claim": "1"}
        ],
        "rejections": [
            {
                "rejection_type": "103",
                "statutory_basis": "35 U.S.C. 103",
                "affected_claims": ["1", "2"],
                "examiner_reasoning": "Claims 1-2 are obvious over Smith in view of Jones.",
                "cited_prior_art": [
                    {
                        "reference_type": "US Patent",
                        "identifier": "US 9,999,999 B2",
                        "title": "Widget Technology",
                        "relevant_claims": ["1"]
                    }
                ]
            }
        ],
        "objections": [],
        "other_statements": []
    }
    
    try:
        oa_enhanced = OfficeActionExtractedData(**enhanced_data)
        print("✓ Enhanced data structure works correctly")
        
        # Verify new fields are accessible
        header = oa_enhanced.header
        assert header.first_named_inventor == "Jane Doe"
        assert header.applicant_name == "Tech Corp Inc."
        assert header.title_of_invention == "Advanced Widget System"
        assert header.customer_number == "12345"
        assert header.examiner_phone == "(571) 272-1000"
        assert header.examiner_email == "john.smith@uspto.gov"
        assert header.examiner_type == "Primary Examiner"
        print("✓ All new fields are accessible")
        
    except Exception as e:
        print(f"✗ Enhanced data structure failed: {e}")
        return False
    
    return True

def test_report_generation():
    """Test that report generation works with enhanced data."""
    print("\nTesting enhanced report generation...")
    
    enhanced_data = {
        "header": {
            "application_number": "16/123,456",
            "filing_date": "2023-06-15",
            "office_action_date": "2024-01-15",
            "office_action_type": "Non-Final",
            "examiner_name": "John Smith",
            "art_unit": "2100",
            "attorney_docket_number": "ABC-001",
            "confirmation_number": "1234",
            "response_deadline": "2024-04-15",
            "first_named_inventor": "Jane Doe",
            "applicant_name": "Tech Corp Inc.",
            "title_of_invention": "Advanced Widget System",
            "customer_number": "12345",
            "examiner_phone": "(571) 272-1000",
            "examiner_email": "john.smith@uspto.gov",
            "examiner_type": "Primary Examiner"
        },
        "claims_status": [
            {"claim_number": "1", "status": "Rejected", "dependency_type": "Independent"}
        ],
        "rejections": [
            {
                "rejection_type": "103",
                "statutory_basis": "35 U.S.C. 103",
                "affected_claims": ["1"],
                "examiner_reasoning": "Claim 1 is obvious over prior art.",
                "cited_prior_art": []
            }
        ],
        "objections": [],
        "other_statements": []
    }
    
    try:
        report_gen = ReportGenerator()
        report_stream = report_gen.generate_office_action_report(enhanced_data)
        
        # Check that we got a valid Word document
        if report_stream and len(report_stream.getvalue()) > 0:
            print("✓ Report generation successful")
            print(f"✓ Generated report size: {len(report_stream.getvalue())} bytes")
            return True
        else:
            print("✗ Report generation failed - empty output")
            return False
            
    except Exception as e:
        print(f"✗ Report generation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Testing Enhanced Office Action Extraction ===\n")
    
    success = True
    
    # Test models
    if not test_enhanced_models():
        success = False
    
    # Test report generation
    if not test_report_generation():
        success = False
    
    print(f"\n=== Test Results ===")
    if success:
        print("✓ All tests passed! Enhanced extraction functionality is working correctly.")
        print("\nNew fields added:")
        print("- Filing Date")
        print("- First Named Inventor")
        print("- Applicant Name/Entity")
        print("- Title of Invention")
        print("- Customer Number")
        print("- Examiner's Phone Number")
        print("- Examiner's Email")
        print("- Examiner Type (Primary/Assistant)")
        print("- Attorney Docket Number (already existed)")
        print("- Confirmation Number (already existed)")
    else:
        print("✗ Some tests failed. Please check the implementation.")
        sys.exit(1)

if __name__ == "__main__":
    main()