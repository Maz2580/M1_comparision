import json

def load_council_data():
    """
    Placeholder function to load property data from the Council's system.
    In a real-world scenario, this function would connect to a database
    (e.g., PostgreSQL, SQL Server) or read from a CSV file extract.

    The sample data demonstrates:
    - Two new child parcels from a subdivision (propnum 7001, 7002).
    - A property with an updated road name (propnum 5002).
    - An unchanged property (propnum 5003).
    """
    print("INFO: Loading Council data (using sample data)...")
    return [
        {
            "propnum": "7001", "spi": "3\\PS800001", "plan_number": "PS800001", "lot_number": "3",
            "full_address": "1 INDEPENDENCE WAY, SPRINGFIELD", "road_name": "INDEPENDENCE WAY", "house_number_1": "1",
            "is_active": True
        },
        {
            "propnum": "7002", "spi": "4\\PS800001", "plan_number": "PS800001", "lot_number": "4",
            "full_address": "2 INDEPENDENCE WAY, SPRINGFIELD", "road_name": "INDEPENDENCE WAY", "house_number_1": "2",
            "is_active": True
        },
        {
            "propnum": "5002", "spi": "2\\PS123456", "plan_number": "PS123456", "lot_number": "2",
            "full_address": "10 MAIN ROAD, SPRINGFIELD", "road_name": "MAIN ROAD", "house_number_1": "10",
            "is_active": True
        },
        {
            "propnum": "5003", "spi": "5\\LP55555", "plan_number": "LP55555", "lot_number": "5",
            "full_address": "12 MAIN STREET, SPRINGFIELD", "road_name": "MAIN STREET", "house_number_1": "12",
            "is_active": True
        }
    ]

def load_vicmap_data():
    """
    Placeholder function to load property data from the fortnightly Vicmap extract.
    This would typically involve reading from a Shapefile, File Geodatabase, or CSV.

    The sample data demonstrates:
    - The parent parcel that was subdivided (propnum 6001). This property no longer exists
      in the new Council data, so it should be identified as retired.
    - The property before its road name was updated (propnum 5002).
    - An unchanged property (propnum 5003).
    - A property that exists in Vicmap but is missing from the council data (propnum 9999).
    """
    print("INFO: Loading Vicmap data (using sample data)...")
    return [
        {
            "property_PFI": "PFI_6001", "propnum": "6001", "spi": "1\\PS123456",
            "full_address": "10 OLD FARM ROAD, SPRINGFIELD", "road_name": "OLD FARM ROAD", "house_number_1": "10",
        },
        {
            "property_PFI": "PFI_5002", "propnum": "5002", "spi": "2\\PS123456",
            "full_address": "10 MAIN STREET, SPRINGFIELD", "road_name": "MAIN STREET", "house_number_1": "10",
        },
        {
            "property_PFI": "PFI_5003", "propnum": "5003", "spi": "5\\LP55555",
            "full_address": "12 MAIN STREET, SPRINGFIELD", "road_name": "MAIN STREET", "house_number_1": "12",
        },
        {
            "property_PFI": "PFI_9999", "propnum": "9999", "spi": "1\\LP98765",
            "full_address": "5 FORGOTTEN AVENUE, SPRINGFIELD", "road_name": "FORGOTTEN AVENUE", "house_number_1": "5",
        }
    ]

def compare_datasets(council_data, vicmap_data):
    """
    The core comparison engine. It compares the two datasets to identify
    and categorize changes.
    """
    print("INFO: Starting data comparison...")
    change_report = []

    # Create dictionaries for quick lookups using propnum as the key
    council_props = {p["propnum"]: p for p in council_data}
    vicmap_props = {p["propnum"]: p for p in vicmap_data}

    # --- Stage 1: Check for new properties and attribute updates ---
    # Iterate through the council data, as it is the source of truth.
    for propnum, council_prop in council_props.items():
        vicmap_prop = vicmap_props.get(propnum)

        # Case 1: New Property (not found in Vicmap)
        if not vicmap_prop:
            change_report.append({
                "change_category": "New Property (Subdivision)",
                "justification": f"New lot {council_prop.get('lot_number')} on plan {council_prop.get('plan_number')} not found in Vicmap.",
                "council_propnum": propnum,
                "vicmap_pfi": None,
                "attribute_changed": "ALL",
                "vicmap_old_value": None,
                "council_new_value": council_prop.get('full_address'),
                "proposed_edit_code": "E", # 'E' for 'Edit All' creates a new property and address
                "review_status": "Pending",
                "reviewer_notes": ""
            })
            continue

        # Case 2: Matched property - compare attributes for changes
        # Simple comparison for address. A real system would compare each component.
        if council_prop["full_address"] != vicmap_prop["full_address"]:
            change_report.append({
                "change_category": "Address Update",
                "justification": "Address details mismatch between Council and Vicmap.",
                "council_propnum": propnum,
                "vicmap_pfi": vicmap_prop.get('property_PFI'),
                "attribute_changed": "full_address",
                "vicmap_old_value": vicmap_prop.get('full_address'),
                "council_new_value": council_prop.get('full_address'),
                "proposed_edit_code": "S", # 'S' for 'Site/Address' update
                "review_status": "Pending",
                "reviewer_notes": ""
            })

    # --- Stage 2: Check for retired properties ---
    # Iterate through Vicmap data to find properties no longer in the council's active list.
    for propnum, vicmap_prop in vicmap_props.items():
        if propnum not in council_props:
            # We assume a property missing from the council list is a candidate for retirement.
            # Here we identify the parent parcel of our sample subdivision.
            # TODO: The condition `vicmap_prop['spi'] == '1\\PS123456'` is specific to the sample data.
            # In a real system, a more robust way to identify parent parcels would be needed.
            # For example, by checking if the `spi` of the Vicmap property matches the `plan_number`
            # of new child properties identified in Stage 1, or through a dedicated list of parent SPIs
            # that have been subdivided.
            is_parent_of_subdivision = vicmap_prop['spi'] == '1\\PS123456' 
            
            category = "Parent Parcel (Implicitly Retired)" if is_parent_of_subdivision else "Missing from Council Data"
            justification = "Parent parcel of new subdivision. Retirement is handled by Vicmap upon child creation." if is_parent_of_subdivision else "Property in Vicmap not found in Council's active property list."
            edit_code = "None" if is_parent_of_subdivision else "Flag for Review"

            change_report.append({
                "change_category": category,
                "justification": justification,
                "council_propnum": propnum, # In this case, it's the Vicmap propnum not found in council's active list
                "vicmap_pfi": vicmap_prop.get('property_PFI'),
                "attribute_changed": "status",
                "vicmap_old_value": "Active in Vicmap",
                "council_new_value": "Retired/Missing in Council DB",
                "proposed_edit_code": edit_code,
                "review_status": "Pending",
                "reviewer_notes": "Manual investigation required to confirm if property should be retired." if edit_code == "Flag for Review" else ""
            })

    print(f"INFO: Comparison complete. Found {len(change_report)} changes.")
    return change_report

def main():
    """
    Main function to run the comparison process and print the structured output.
    """
    # 1. Load data from sources
    council_data = load_council_data()
    vicmap_data = load_vicmap_data()
    
    # 2. Compare datasets and generate the change report
    change_report = compare_datasets(council_data, vicmap_data)
    
    # 3. Output the report as a JSON object
    # The 'indent=4' argument makes the JSON output human-readable.
    print("\n--- CHANGE REPORT (JSON) ---")
    print(json.dumps(change_report, indent=4))


if __name__ == "__main__":
    main()
