"""
Advanced PDF Validator - Checks for common compatibility issues
"""
import sys
import os

def validate_pdf_professional(pdf_path):
    """Deep validation of PDF for website compatibility"""
    issues = []
    warnings = []
    
    try:
        import pikepdf
    except ImportError:
        print("ERROR: pikepdf not installed. Run: pip install pikepdf")
        return
    
    print(f"\n{'='*60}")
    print(f"PDF Validation Report: {os.path.basename(pdf_path)}")
    print(f"{'='*60}\n")
    
    try:
        pdf = pikepdf.open(pdf_path)
        
        # Basic Info
        print(f"📄 PDF Version: {pdf.pdf_version}")
        print(f"📄 Pages: {len(pdf.pages)}")
        print(f"📄 Encrypted: {pdf.is_encrypted}")
        print()
        
        # Metadata Check
        print("🔍 Metadata Check:")
        with pdf.open_metadata() as meta:
            pdfaid_part = meta.get('pdfaid:part', None)
            pdfaid_conformance = meta.get('pdfaid:conformance', None)
            
            if pdfaid_part:
                print(f"  ✓ PDF/A Part: {pdfaid_part}")
            else:
                issues.append("PDF/A Part metadata missing")
                print(f"  ✗ PDF/A Part: MISSING")
            
            if pdfaid_conformance:
                print(f"  ✓ PDF/A Conformance: {pdfaid_conformance}")
            else:
                issues.append("PDF/A Conformance metadata missing")
                print(f"  ✗ PDF/A Conformance: MISSING")
            
            creator = meta.get('dc:creator', None)
            print(f"  {'✓' if creator else '✗'} Creator: {creator or 'MISSING'}")
        
        print()
        
        # Color Space Check
        print("🎨 Color Space Check:")
        page = pdf.pages[0]
        if '/ColorSpace' in page:
            print(f"  ✓ ColorSpace defined")
        else:
            warnings.append("No explicit ColorSpace (might be embedded in image)")
            print(f"  ⚠ ColorSpace not explicitly defined")
        
        print()
        
        # FontDescriptor Check (PDF/A requirement)
        print("📝 Font Check:")
        fonts_ok = True
        if '/Font' in page.get('/Resources', {}):
            print(f"  ⚠ Fonts present (image-only PDFs shouldn't have fonts)")
            warnings.append("Fonts detected in image-only PDF")
        else:
            print(f"  ✓ No fonts (correct for image PDF)")
        
        print()
        
        # OutputIntent Check (Critical for PDF/A)
        print("🎯 OutputIntent Check (Critical!):")
        if '/OutputIntents' in pdf.Root:
            print(f"  ✓ OutputIntents present")
        else:
            issues.append("OutputIntents missing (required for PDF/A)")
            print(f"  ✗ OutputIntents MISSING - This is likely the problem!")
        
        print()
        
        # XMP Metadata
        print("📋 XMP Metadata Check:")
        if '/Metadata' in pdf.Root:
            print(f"  ✓ XMP Metadata stream present")
        else:
            warnings.append("XMP Metadata stream missing")
            print(f"  ⚠ XMP Metadata stream missing")
        
        pdf.close()
        
    except Exception as e:
        issues.append(f"Failed to open PDF: {e}")
        print(f"✗ ERROR: {e}")
    
    # Summary
    print()
    print(f"{'='*60}")
    print("SUMMARY:")
    print(f"{'='*60}")
    
    if not issues:
        print("✅ No critical issues found")
    else:
        print(f"❌ {len(issues)} CRITICAL ISSUE(S):")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    
    if warnings:
        print(f"\n⚠️  {len(warnings)} WARNING(S):")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
    
    print()
    
    if issues:
        print("🔧 RECOMMENDATION:")
        print("   The PDF is missing OutputIntents (required for PDF/A).")
        print("   This is the most common reason websites reject PDFs.")
        print("   I need to enhance the converter to embed ICC profiles.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_pdf.py <path_to_pdf>")
        print("\nTesting with example PDF...")
        if os.path.exists("test_pdfs/test_rgba_transparent_professional.pdf"):
            validate_pdf_professional("test_pdfs/test_rgba_transparent_professional.pdf")
    else:
        validate_pdf_professional(sys.argv[1])
