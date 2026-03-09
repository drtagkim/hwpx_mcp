import os
import zipfile
import tempfile
import shutil
import xml.etree.ElementTree as ET
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("hwpx-parser")

# Standard HWPX Namespaces
HWPX_NAMESPACES = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hhs": "http://www.hancom.co.kr/hwpml/2011/history",
    "hm": "http://www.hancom.co.kr/hwpml/2011/master-page",
    "hpf": "http://www.hancom.co.kr/hwpml/2011/chart",
    "dc": "http://purl.org/dc/elements/1.1/",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "ep": "http://www.hancom.co.kr/hwpml/2011/epub",
    "ocf": "urn:oasis:names:tc:opendocument:xmlns:container"
}

for prefix, uri in HWPX_NAMESPACES.items():
    ET.register_namespace(prefix, uri)

class HWPXModifier:
    """Context manager for safely unpacking, modifying, and repacking HWPX files."""
    def __init__(self, source_path: str, target_path: str):
        self.source_path = source_path
        self.target_path = target_path
        self.tmpdir = None

    def __enter__(self):
        self.tmpdir = tempfile.mkdtemp()
        with zipfile.ZipFile(self.source_path, 'r') as zf:
            zf.extractall(self.tmpdir)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Repackage the HWPX
            with zipfile.ZipFile(self.target_path, 'w') as zf:
                mimetype_path = os.path.join(self.tmpdir, "mimetype")
                if os.path.exists(mimetype_path):
                    zf.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
                
                for root, dirs, files in os.walk(self.tmpdir):
                    for file in files:
                        if file == "mimetype" and root == self.tmpdir:
                            continue
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_path, self.tmpdir)
                        zf.write(abs_path, rel_path, compress_type=zipfile.ZIP_DEFLATED)
        
        # Cleanup temp directory
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def get_section_xml_paths(self):
        contents_dir = os.path.join(self.tmpdir, "Contents")
        if not os.path.exists(contents_dir):
            return []
        
        section_files = []
        for f in os.listdir(contents_dir):
            if f.startswith('section') and f.endswith('.xml'):
                section_files.append(os.path.join(contents_dir, f))
        section_files.sort()
        return section_files
    
    def get_bindata_path(self):
        return os.path.join(self.tmpdir, "BinData")


def extract_text_from_xml(xml_content: bytes) -> str:
    """Extracts text from HWPX section XML (specifically from <hp:t> tags)."""
    try:
        root = ET.fromstring(xml_content)
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
    """Read an HWPX file and extract all text content from it."""
    if not os.path.exists(file_path):
        return f"Error: File not found exactly at {file_path}"
    
    try:
        extracted_text = []
        with zipfile.ZipFile(file_path, 'r') as zf:
            file_list = zf.namelist()
            section_files = [f for f in file_list if f.startswith('Contents/section') and f.endswith('.xml')]
            if not section_files:
                return "Error: Could not find any section XML data inside the HWPX file."
            
            section_files.sort()
            for section_file in section_files:
                xml_content = zf.read(section_file)
                text = extract_text_from_xml(xml_content)
                extracted_text.append(text)
                
        return "\n\n".join(extracted_text)
    except Exception as e:
        return f"Error: An unexpected error occurred while reading {file_path} - {str(e)}"


@mcp.tool()
def list_hwpx_files(directory_path: str) -> list[str]:
    """List all HWPX files in a given directory."""
    if not os.path.exists(directory_path):
        return [f"Error: Directory not found at {directory_path}"]
    
    hwpx_files = []
    try:
        for f in os.listdir(directory_path):
            if f.lower().endswith('.hwpx'):
                hwpx_files.append(os.path.join(directory_path, f))
        return hwpx_files
    except Exception as e:
        return [f"Error reading directory: {str(e)}"]


# -----------------------------------------------------------------------------------------
# NEW: HWPX Advanced Table & Image Manipulations
# -----------------------------------------------------------------------------------------

def _find_table_by_index(root, table_idx, ns_match='}tbl'):
    """Helper to find the nth table recursively across the document section."""
    tbl_count = 0
    for elem in root.iter():
        if elem.tag.endswith(ns_match):
            if tbl_count == table_idx:
                return elem
            tbl_count += 1
    return None

def _clear_cell_text(cell_elem):
    """Helper to clear text content of a cell <hp:tc>."""
    for t in cell_elem.iter():
        if t.tag.endswith('}t') or t.tag == 't':
            t.text = ""

@mcp.tool()
def update_hwpx_table_content(file_path: str, target_path: str, table_index: int, row_index: int, col_index: int, new_text: str) -> str:
    """
    Update text inside a specific cell of an HWPX table.
    Indices are 0-based.
    """
    try:
        with HWPXModifier(file_path, target_path) as hwpx:
            # We assume tables are in the first section for simplicity, but we will scan all.
            # Realistically, tables cross sections, so we maintain a global table index.
            global_tbl_count = 0
            updated = False
            
            for section_path in hwpx.get_section_xml_paths():
                tree = ET.parse(section_path)
                root = tree.getroot()
                
                # Register namespaces to prevent ns0, ns1 junk when writing
                # Typical HWPX namespaces are registered globally at the top
                for tbl in root.iter():
                    if tbl.tag.endswith('}tbl'):
                        if global_tbl_count == table_index:
                            # Find the row
                            rows = [tr for tr in tbl if tr.tag.endswith('}tr')]
                            if row_index < len(rows):
                                tr = rows[row_index]
                                # Find the cell
                                cells = [tc for tc in tr if tc.tag.endswith('}tc')]
                                if col_index < len(cells):
                                    tc = cells[col_index]
                                    # Find the first text tag and replace, clear others to be safe
                                    text_nodes = [t for t in tc.iter() if t.tag.endswith('}t')]
                                    if text_nodes:
                                        text_nodes[0].text = new_text
                                        for t in text_nodes[1:]:
                                            t.text = ""
                                        updated = True
                                        break
                        global_tbl_count += 1
                
                if updated:
                    with open(section_path, 'wb') as f:
                        f.write(b'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
                        tree.write(f, encoding='UTF-8', xml_declaration=False)
                    return f"Successfully updated table {table_index}, cell({row_index},{col_index}) in {target_path}"
                    
        return f"Could not find table {table_index} or cell({row_index},{col_index})"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def modify_hwpx_table_row(file_path: str, target_path: str, table_index: int, row_index: int, action: str) -> str:
    """
    Add or delete a row in an HWPX table.
    Action: 'add' (duplicates the last row and inserts at row_index) or 'delete'.
    """
    import copy
    try:
        with HWPXModifier(file_path, target_path) as hwpx:
            global_tbl_count = 0
            updated = False
            
            for section_path in hwpx.get_section_xml_paths():
                tree = ET.parse(section_path)
                root = tree.getroot()
                
                for tbl in root.iter():
                    if tbl.tag.endswith('}tbl'):
                        if global_tbl_count == table_index:
                            rows = [tr for tr in tbl if tr.tag.endswith('}tr')]
                            
                            if action == 'delete' and row_index < len(rows):
                                tbl.remove(rows[row_index])
                                updated = True
                            
                            elif action == 'add':
                                if rows:
                                    # Duplicate the last row to preserve formatting
                                    new_row = copy.deepcopy(rows[-1])
                                    # Clear text in the new row
                                    for cell in new_row:
                                        if cell.tag.endswith('}tc'):
                                            _clear_cell_text(cell)
                                    
                                    # Reset paragraph IDs to avoid duplicate ID corruption in HWPX
                                    for p in new_row.iter():
                                        if p.tag.endswith('}p'):
                                            if 'id' in p.attrib and p.attrib['id'] != '0':
                                                p.attrib['id'] = '0'
                                                
                                    # Insert at requested index
                                    insert_pos = min(row_index, len(tbl))
                                    tbl.insert(insert_pos, new_row)
                                    updated = True
                        global_tbl_count += 1
                
                if updated:
                    with open(section_path, 'wb') as f:
                        f.write(b'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
                        tree.write(f, encoding='UTF-8', xml_declaration=False)
                    return f"Successfully performed '{action}' on table {table_index}, row {row_index} in {target_path}"
                    
        return f"Could not perform action '{action}' on table {table_index}."
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def delete_hwpx_table(file_path: str, target_path: str, table_index: int) -> str:
    """Delete an entire table from the HWPX document by its index."""
    try:
        with HWPXModifier(file_path, target_path) as hwpx:
            global_tbl_count = 0
            updated = False
            
            for section_path in hwpx.get_section_xml_paths():
                tree = ET.parse(section_path)
                root = tree.getroot()
                
                # Tables are usually inside paragraphs (<hp:p> -> <hp:run> -> <hp:tbl>)
                # We need to find the parent to remove the table
                # A simple recursion to track parents:
                parent_map = {c: p for p in root.iter() for c in p}
                
                for tbl in root.iter():
                    if tbl.tag.endswith('}tbl'):
                        if global_tbl_count == table_index:
                            parent = parent_map.get(tbl)
                            if parent is not None:
                                parent.remove(tbl)
                                updated = True
                        global_tbl_count += 1
                
                if updated:
                    with open(section_path, 'wb') as f:
                        f.write(b'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
                        tree.write(f, encoding='UTF-8', xml_declaration=False)
                    return f"Successfully deleted table {table_index} and saved to {target_path}"
                    
        return f"Could not find table {table_index} to delete."
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def copy_hwpx_table(file_path: str, target_path: str, source_table_index: int, target_paragraph_index: int) -> str:
    """
    Copies an entire table (as a template) and inserts it after a specific paragraph.
    Note: Highly experimental. Works best for simple document structures.
    """
    import copy
    try:
        with HWPXModifier(file_path, target_path) as hwpx:
            global_tbl_count = 0
            global_p_count = 0
            table_to_copy = None
            updated = False
            
            # First pass: Find the table
            for section_path in hwpx.get_section_xml_paths():
                tree = ET.parse(section_path)
                for tbl in tree.getroot().iter():
                    if tbl.tag.endswith('}tbl'):
                        if global_tbl_count == source_table_index:
                            table_to_copy = copy.deepcopy(tbl)
                        global_tbl_count += 1
                        
            if table_to_copy is None:
                return f"Could not find source table {source_table_index}."

            # Second pass: Find paragraph and insert
            for section_path in hwpx.get_section_xml_paths():
                tree = ET.parse(section_path)
                root = tree.getroot()
                
                parent_map = {c: p for p in root.iter() for c in p}
                
                for p_elem in root.iter():
                    if p_elem.tag.endswith('}p'):
                        if global_p_count == target_paragraph_index:
                            # HWPX expects tables inside a <hp:run>. Let's create a minimal run if needed, 
                            # or just append to the paragraph.
                            parent_run = ET.Element("{http://www.hancom.co.kr/hwpml/2011/paragraph}run")
                            parent_run.append(table_to_copy)
                            p_elem.append(parent_run)
                            updated = True
                            
                        global_p_count += 1
                
                if updated:
                    with open(section_path, 'wb') as f:
                        f.write(b'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
                        tree.write(f, encoding='UTF-8', xml_declaration=False)
                    return f"Successfully copied table {source_table_index} to paragraph {target_paragraph_index}."

        return f"Could not find paragraph {target_paragraph_index}."
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def replace_hwpx_image(file_path: str, target_path: str, image_index: int, new_image_path: str) -> str:
    """
    Replace an image in the HWPX document, keeping its structural constraints (size, position).
    Image indices are 0-based and sorted alphabetically by their binary filename in BinData/
    """
    if not os.path.exists(new_image_path):
        return f"Error: Replacement image not found at {new_image_path}"

    try:
        with HWPXModifier(file_path, target_path) as hwpx:
            bindata_dir = hwpx.get_bindata_path()
            if not os.path.exists(bindata_dir):
                return "Error: No BinData directory found in this HWPX document (it contains no images)."
            
            # List binary files (these are the images/assets)
            binary_files = os.listdir(bindata_dir)
            
            # Filter standard image extensions found in HWPX (png, jpg, jpeg, gif, bmp, wmf)
            image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.wmf')
            image_files = [f for f in binary_files if f.lower().endswith(image_extensions)]
            image_files.sort()
            
            if image_index >= len(image_files):
                return f"Error: Image index {image_index} out of bounds. Found {len(image_files)} images."
            
            target_image_filename = image_files[image_index]
            target_image_filepath = os.path.join(bindata_dir, target_image_filename)
            
            # Simply overwrite the target binary file with the new image.
            # HWPX renders it inside the pre-defined bounding box from XML.
            shutil.copy2(new_image_path, target_image_filepath)
            
        return f"Successfully replaced image {image_index} ({target_image_filename}) in {target_path}"
    
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    mcp.run()
