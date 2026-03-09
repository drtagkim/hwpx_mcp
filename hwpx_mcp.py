import os
import zipfile
import xml.etree.ElementTree as ET
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("hwpx-parser")

def extract_text_from_xml(xml_content: bytes) -> str:
    """Extracts text from HWPX section XML (specifically from <hp:t> tags)."""
    try:
        root = ET.fromstring(xml_content)
        # HWPX namespaces usually look like: xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"
        # We can just search for all tags ending with 't' to be safe against namespace variations
        text_parts = []
        for elem in root.iter():
            if elem.tag.endswith('}t') or elem.tag == 't':
                if elem.text:
                    text_parts.append(elem.text)
        return "".join(text_parts)
    except Exception as e:
        return f"[XML Parsing Error: {str(e)}]"

@mcp.tool()
def read_hwpx(file_path: str) -> str:
    """
    Read an HWPX file and extract all text content from it.
    
    Args:
        file_path: The absolute path to the .hwpx file.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found exactly at {file_path}"
    
    if not file_path.lower().endswith('.hwpx'):
        return f"Error: Only .hwpx files are supported. Provided: {file_path}"

    try:
        extracted_text = []
        with zipfile.ZipFile(file_path, 'r') as zf:
            # Look for section XMLs, usually in Contents/
            # Example: Contents/section0.xml
            file_list = zf.namelist()
            section_files = [f for f in file_list if f.startswith('Contents/section') and f.endswith('.xml')]
            
            if not section_files:
                return "Error: Could not find any section XML data inside the HWPX file."
            
            # Sort them to ensure order (section0, section1, etc.)
            section_files.sort()
            
            for section_file in section_files:
                xml_content = zf.read(section_file)
                text = extract_text_from_xml(xml_content)
                extracted_text.append(text)
                
        # Join sections with double newlines
        return "\n\n".join(extracted_text)
    
    except zipfile.BadZipFile:
        return f"Error: Failed to open {file_path}. It might not be a valid HWPX/ZIP file."
    except Exception as e:
        return f"Error: An unexpected error occurred while reading {file_path} - {str(e)}"

@mcp.tool()
def list_hwpx_files(directory_path: str) -> list[str]:
    """
    List all HWPX files in a given directory.
    
    Args:
        directory_path: The absolute path to the directory to search.
    """
    if not os.path.exists(directory_path):
        return [f"Error: Directory not found at {directory_path}"]
    
    if not os.path.isdir(directory_path):
        return [f"Error: Path is not a directory: {directory_path}"]
    
    hwpx_files = []
    try:
        for f in os.listdir(directory_path):
            if f.lower().endswith('.hwpx'):
                hwpx_files.append(os.path.join(directory_path, f))
        return hwpx_files
    except Exception as e:
        return [f"Error reading directory {directory_path}: {str(e)}"]

if __name__ == "__main__":
    # Start the FastMCP server via stdio
    mcp.run()
