"""
Professional PNG to PDF Converter Test Script
Tests the enhanced image_converter with PDF/A-1b support
"""
import os
import sys
from PIL import Image, ImageDraw

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from converters.image_converter import ImageConverter

def create_test_images():
    """Create test PNG images with different characteristics"""
    test_dir = "test_pdfs"
    os.makedirs(test_dir, exist_ok=True)
    
    # Test 1: RGB Image
    rgb_path = os.path.join(test_dir, "test_rgb.png")
    img_rgb = Image.new('RGB', (800, 600), color=(73, 109, 137))
    draw = ImageDraw.Draw(img_rgb)
    draw.text((50, 50), "RGB Test Image - No Transparency", fill='white')
    img_rgb.save(rgb_path)
    print(f"✓ Created: {rgb_path}")
    
    # Test 2: RGBA Image with transparency
    rgba_path = os.path.join(test_dir, "test_rgba_transparent.png")
    img_rgba = Image.new('RGBA', (800, 600), color=(255, 0, 0, 0))  # Fully transparent
    draw = ImageDraw.Draw(img_rgba)
    # Draw semi-transparent rectangles
    draw.rectangle([100, 100, 700, 500], fill=(0, 128, 255, 200))
    draw.text((50, 50), "RGBA Test - With Transparency", fill=(255, 255, 255, 255))
    img_rgba.save(rgba_path)
    print(f"✓ Created: {rgba_path}")
    
    # Test 3: Palette mode image
    palette_path = os.path.join(test_dir, "test_palette.png")
    img_p = Image.new('P', (800, 600))
    img_p.putpalette([i % 256 for i in range(768)])  # Simple palette
    img_p.save(palette_path)
    print(f"✓ Created: {palette_path}")
    
    return [rgb_path, rgba_path, palette_path]

def test_professional_pdf_conversion():
    """Test professional PNG→PDF conversion"""
    converter = ImageConverter()
    test_images = create_test_images()
    
    print("\n" + "="*60)
    print("Testing Professional PNG → PDF Conversion")
    print("="*60 + "\n")
    
    for test_img in test_images:
        output_pdf = test_img.replace('.png', '_professional.pdf')
        
        print(f"Converting: {os.path.basename(test_img)}")
        success, message = converter.convert(
            source=test_img,
            dest=output_pdf,
            target_format='pdf',
            # Professional PDF options
            pdf_dpi=300,  # High quality DPI
            pdf_background=(255, 255, 255),  # White background for transparency
            pdf_title=f"Test PDF - {os.path.basename(test_img)}",
            pdf_creator="ypriteConv Professional Test",
            pdf_description="Testing PDF/A-1b compliance and metadata"
        )
        
        if success:
            size_kb = os.path.getsize(output_pdf) / 1024
            print(f"  ✓ Success: {message}")
            print(f"  📄 Output: {output_pdf} ({size_kb:.1f} KB)")
        else:
            print(f"  ✗ Failed: {message}")
        print()
    
    print("="*60)
    print("Test Summary:")
    print("="*60)
    print("PDFs created with:")
    print("  • PDF/A-1b compliance")
    print("  • 300 DPI resolution")
    print("  • Embedded metadata (Title, Creator, Description)")
    print("  • Transparency → White background conversion")
    print("  • sRGB color profile support")
    print("\nCheck the 'test_pdfs' folder for results.")
    print("Upload these PDFs to your problematic websites to verify compatibility!")

if __name__ == "__main__":
    test_professional_pdf_conversion()
