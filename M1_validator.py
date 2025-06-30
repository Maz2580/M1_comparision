# m1_validator.py

import pandas as pd
import requests
import io

# --- Step 1: Define Sample Rates Data Structure (Modified for Testing) ---
sample_rates_data = [
    # Scenario 1: Matches M1 propnum 171763.0 (edit_code 'A' - new property)
    {
        "propnum": "171763.0", "spi": "2\\PS828727", "property_pfi": "PFI_RATES_171763", # Made up PFI
        "address_full": "71 GOWRIE STREET TATURA", "lot_number": "2", "plan_number": "PS828727",
        "status": "C",
        "Memo": "New child parcel from subdivision PS828727. Processing complete. council approved."
    },
    # Scenario 2: Matches M1 propnum 171764.0 (edit_code 'S' - address change)
    {
        "propnum": "171764.0", "spi": "1\\PS828727", "property_pfi": "PFI_RATES_171764", # Made up PFI
        "address_full": "71a gowrie street tatura", "lot_number": "1", "plan_number": "PS828727", # Address matches M1 target
        "status": "C",
        "Memo": "Address allocation for 71A GOWRIE STREET TATURA completed 2024-05-01. Verified update."
    },
    # Scenario 3: NC test - Using a propnum that MIGHT exist in M1, if not, will be "Not Found"
    # We'll make its memo suitable for an NC pass if found.
    {
        "propnum": "181833.0", "spi": "1\\PS849482", "property_pfi": "PFI_RATES_181833", 
        "address_full": "320 VERNEY ROAD SHEPPARTON NORTH", 
        "status": "C",
        "Memo": "Standard active property. No significant actions recorded recently." # Suitable for NC
    },
    # Scenario 4: Matches M1 spi 3\PS423158 (edit_code 'R' - Retirement)
    {
        "propnum": "199533.0", # Propnum from M1 comment for this SPI
        "spi": "3\\PS423158", "property_pfi": "130692255.0", # PFI from M1 for this SPI
        "address_full": "OLD ADDRESS FOR 3\\PS423158", "lot_number": "3", "plan_number": "PS423158",
        "status": "I", # Inactive
        "Memo": "Parcel retired as per council resolution CR123/2024 on 2024-01-01. No longer active. Part of multi-assessment removal."
    },
    # Original samples (can be kept for broader non-match testing or removed if causing confusion)
    {
        "propnum": "1001", "spi": "1\\PS123456", "property_pfi": "PFI_RATES_1001",
        "address_full": "10 OLD STREET, SHEPPARTON", "lot_number": "1", "plan_number": "PS123456",
        "status": "C",
        "Memo": "Property active. Parent parcel for subdivision PS800001 initiated 2024-03-15. Children are props 2001, 2002. This parcel (1001) to be retired upon completion."
    },
    {
        "propnum": "3001", "spi": "5\\LP67890", "property_pfi": "PFI_RATES_3001",
        "address_full": "25 MAIN ROAD, KIALLA", "lot_number": "5", "plan_number": "LP67890",
        "status": "C",
        "Memo": "Address change request processed 2024-02-20. Old address: 25 OLD TRACK, KIALLA. Road name officially changed by council."
    }
]

# --- Step 2: Implement Simulated Rates Lookup Function ---
def get_rates_data(propnum_csv, spi_csv, pfi_csv, current_sample_rates_data):
    propnum_csv = str(propnum_csv).strip() if propnum_csv and str(propnum_csv).lower() != 'nan' else None
    spi_csv = str(spi_csv).strip() if spi_csv and str(spi_csv).lower() != 'nan' else None
    pfi_csv = str(pfi_csv).strip() if pfi_csv and str(pfi_csv).lower() != 'nan' else None

    if propnum_csv:
        for record in current_sample_rates_data:
            if record.get("propnum") == propnum_csv and record.get("status") == "C":
                return record
        for record in current_sample_rates_data: # Check inactive if no current found
            if record.get("propnum") == propnum_csv:
                return record
    if spi_csv:
        for record in current_sample_rates_data:
            if record.get("spi") == spi_csv and record.get("status") == "C":
                return record
        for record in current_sample_rates_data: # Check inactive
            if record.get("spi") == spi_csv:
                return record
    if pfi_csv:
        for record in current_sample_rates_data:
            if record.get("property_pfi") and record.get("property_pfi").endswith(pfi_csv) and record.get("status") == "C": # Basic PFI match
                return record
        for record in current_sample_rates_data: # Check inactive
             if record.get("property_pfi") and record.get("property_pfi").endswith(pfi_csv):
                return record
    return None

# --- Step 3: Implement Core Validation Logic Function ---
def validate_m1_row(m1_row_data, rates_record):
    edit_code = str(m1_row_data.get('edit_code', '')).strip().upper()
    # Pozi CSV has column names with leading spaces. Access them accordingly.
    # Using .get(column, '') or .get(column_with_space, '') for safety
    # Standardized column names are used now, so direct access like row.get('comments') is fine.
    m1_comments = str(m1_row_data.get('comments', '')).strip().lower()
    m1_plan_number = str(m1_row_data.get('plan_number', '')).strip()
    m1_propnum_val = str(m1_row_data.get('propnum','')).strip() # Used for logging/messages

    if not rates_record:
        return f"Needs Review: Property ({m1_propnum_val}/{m1_row_data.get('spi','')}) not found/active in Rates DB"

    rates_memo = str(rates_record.get('Memo', '')).strip().lower()
    rates_status = str(rates_record.get('status', '')).strip().upper()
    
    # New Properties / Subdivisions / Additions (e.g. new assessment to existing parcel)
    # 'A' is often "Add Address" or "Add Property" in Pozi M1.
    # 'P' can be "Property Edit" - sometimes used for new propnums on existing parcels.
    if edit_code in ['A', 'E', 'ECN', 'ENS', 'EAS', 'CRPROPADD', 'NEWPROP', 'ADDPROP', 'ADDADD', 'P']: 
        keywords_in_memo = ["subdivision", "new lot", "child parcel", "severance", "split", "created", "new assessment"]
        memo_has_keywords = any(kw in rates_memo for kw in keywords_in_memo)
        plan_in_memo = m1_plan_number and m1_plan_number.lower() in rates_memo
        
        keywords_in_m1_comments = ["subdivision", "new lot", "child", "adding propnum", "new multi-assessment"]
        m1_comment_has_keywords = any(kw in m1_comments for kw in keywords_in_m1_comments)
        plan_in_m1_comments = m1_plan_number and m1_plan_number.lower() in m1_comments

        if memo_has_keywords or plan_in_memo:
            if rates_status == 'C':
                 return f"OK: New/Related entity ({edit_code}) aligns with Rates Memo (e.g., activity for plan {m1_plan_number or 'N/A'})"
            else:
                 return f"Review: New/Related entity ({edit_code}) - Rates record is Inactive. Memo: {rates_memo[:100]}"
        elif m1_comment_has_keywords or plan_in_m1_comments:
             return f"OK: New/Related entity ({edit_code}) aligns with M1 comments (e.g. activity for plan {m1_plan_number or 'N/A'}). Rates Memo does not explicitly confirm."
        else:
            return f"Needs Review: New/Related entity ({edit_code}). Rates Memo ('{rates_memo[:50]}...') does not clearly confirm. M1 Comments: '{m1_comments[:50]}...'"

    # Address/Site Changes
    elif edit_code in ['S', 'SC', 'CAD', 'CHGADD', 'CHGPROP']:
        # Construct the M1 proposed address string more carefully
        m1_addr_parts = []
        if pd.notna(m1_row_data.get('blg_unit_id_1')): # Simplified unit handling
            m1_addr_parts.append(str(m1_row_data.get('blg_unit_type','')).strip())
            m1_addr_parts.append(str(m1_row_data.get('blg_unit_id_1','')).strip())
        if pd.notna(m1_row_data.get('house_number_1')):
            m1_addr_parts.append(str(m1_row_data.get('house_number_1','')).replace('.0','')) # remove .0 from float
        if pd.notna(m1_row_data.get('house_suffix_1')):
             m1_addr_parts.append(str(m1_row_data.get('house_suffix_1','')).strip())
        m1_addr_parts.append(str(m1_row_data.get('road_name','')).strip())
        m1_addr_parts.append(str(m1_row_data.get('road_type','')).strip())
        m1_addr_parts.append(str(m1_row_data.get('locality_name','')).strip())
        m1_new_address_val = ' '.join(filter(None, m1_addr_parts)).strip().lower().replace('  ',' ')
        
        # If council_val is present and looks like a full address, prefer it.
        council_val_addr = str(m1_row_data.get('council_val', '')).strip().lower()
        if len(council_val_addr) > 10 and any(c.isalpha() for c in council_val_addr) and any(c.isdigit() for c in council_val_addr) : # Heuristic for a full address
            m1_new_address_val = council_val_addr


        rates_address = str(rates_record.get('address_full', '')).strip().lower()
        
        change_keywords_in_memo = ["address change", "road name change", "renumber", "address update", "site address modified"]
        memo_supports_change = any(kw in rates_memo for kw in change_keywords_in_memo)

        change_keywords_in_m1_comments = ["address change", "road name", "renumber", "assigning new address", "replacing address"]
        m1_comment_supports_change = any(kw in m1_comments for kw in change_keywords_in_m1_comments)

        if memo_supports_change:
            if m1_new_address_val and m1_new_address_val == rates_address:
                return f"OK: Address change ({edit_code}) reflected in Rates (Address & Memo match: '{m1_new_address_val}')."
            elif "old address" in rates_memo and str(m1_row_data.get('vicmap_val','')).lower() in rates_memo:
                 return f"OK: Address change ({edit_code}) from VM '{m1_row_data.get('vicmap_val','')}' to CL '{m1_new_address_val}' supported by Rates Memo."
            else:
                 return f"OK: Address change ({edit_code}) supported by Rates Memo. Review M1 Addr:'{m1_new_address_val}' vs Rates Addr:'{rates_address}'."
        elif m1_comment_supports_change:
            return f"OK: Address change ({edit_code}) aligns with M1 comments. Rates Memo ('{rates_memo[:50]}...') does not explicitly confirm."
        else:
            return f"Needs Review: Address change ({edit_code}). Memo ('{rates_memo[:50]}...') & M1 Comments ('{m1_comments[:50]}...') do not clearly confirm."

    # Retirements / Consolidations
    elif edit_code in ['R', 'RCN', 'RET', 'RC', 'DELPROP', 'REMPROP', 'REMADD', 'DELADD']: 
        retirement_keywords_in_memo = ["consolidated", "retired", "parent parcel", "no longer active", "demolished"]
        memo_supports_retirement = any(kw in rates_memo for kw in retirement_keywords_in_memo)
        
        retirement_keywords_in_m1_comments = ["removing propnum", "retiring", "consolidation"]
        m1_comment_supports_retirement = any(kw in m1_comments for kw in retirement_keywords_in_m1_comments)

        if rates_status == 'I': # Property is Inactive in Rates
            if memo_supports_retirement:
                return f"OK: Retirement ({edit_code}) aligns with Inactive status and Memo in Rates (Memo: '{rates_memo[:50]}...')."
            else: # Inactive, but memo doesn't confirm reason
                return f"OK: Retirement ({edit_code}) aligns with Inactive status in Rates. Memo ('{rates_memo[:50]}...') less specific on reason."
        elif memo_supports_retirement : # Active in rates, but memo suggests retirement
             return f"Review: Retirement ({edit_code}). Rates status is ACTIVE, but Memo ('{rates_memo[:50]}...') suggests retirement. Check status."
        elif m1_comment_supports_retirement:
            return f"Review: Retirement ({edit_code}) per M1 comments. Rates status is ACTIVE. Memo ('{rates_memo[:50]}...') not confirming."
        else:
            return f"Needs Review: Retirement ({edit_code}). Rates status is ACTIVE. Memo ('{rates_memo[:50]}...') and M1 Comments ('{m1_comments[:50]}...') do not clearly confirm."
            
    elif edit_code in ['NC', 'N', 'NOCHANGE']:
        # For NC, ideally memo shows no conflicting activity.
        no_conflict_keywords = ["change", "subdivision", "new", "update", "consolidat", "retir", "error", "correct"]
        if rates_memo and not any(kw in rates_memo for kw in no_conflict_keywords):
            return f"OK: No Change ({edit_code}) aligns with uneventful Rates Memo."
        elif not rates_memo: # No memo often means no recent activity.
             return f"OK: No Change ({edit_code}). No specific Memo in Rates."
        else: # Memo has activity, but M1 says NC
            return f"Review: No Change ({edit_code}), but Rates Memo ('{rates_memo[:50]}...') mentions some activity. Verify if related."
            
    # Catch-all for other edit codes or less clear situations
    # C often means "Crefno change" - usually minor administrative update.
    elif edit_code in ['C', 'CREFNO']:
        if "crefno" in m1_comments or "council reference" in m1_comments:
            return f"OK: Crefno update ({edit_code}) noted in M1 comments. Usually minor."
        else:
            return f"Review: Crefno update ({edit_code}). M1 comments ('{m1_comments[:50]}...') unclear. Rates Memo: ('{rates_memo[:50]}...')."
    else: 
        if m1_comments and len(m1_comments) > 3 and any(mc_word in rates_memo for mc_word in m1_comments.split() if len(mc_word)>3) : 
            return f"OK: M1 Comment ('{m1_comments[:50]}...') may align with Rates Memo ('{rates_memo[:50]}...'). Edit Code: {edit_code}."
        elif m1_comments and len(m1_comments) > 3 :
            return f"Review: Edit Code {edit_code}. M1 Comment ('{m1_comments[:50]}...'). Rates Memo ('{rates_memo[:50]}...') may differ or lack detail."
        else: 
            return f"Needs General Review: Edit Code {edit_code}. No/brief M1 comments. Rates Memo: '{rates_memo[:50]}...'."


# --- Main Script Logic ---
def main():
    print("Starting M1 Validation Process...")

    csv_url = "https://raw.githubusercontent.com/Maz2580/M1_comparision/main/M1_Shepparton_2025-04-29_Pozi-Connect-2-10-0.csv"
    output_filename = "M1_Shepparton_validated.csv"
    
    try:
        print(f"Downloading M1 CSV from {csv_url}...")
        response = requests.get(csv_url)
        response.raise_for_status() 
        csv_content = response.content.decode('utf-8-sig') # Use utf-8-sig to handle potential BOM
        m1_df = pd.read_csv(io.StringIO(csv_content))
        print(f"Successfully loaded M1 CSV into DataFrame. Shape: {m1_df.shape}")
        # Standardize column names by stripping leading/trailing spaces
        m1_df.columns = [col.strip() for col in m1_df.columns]
        print("Standardized DataFrame column names.")

    except requests.exceptions.RequestException as e:
        print(f"Error downloading M1 CSV: {e}")
        return
    except pd.errors.EmptyDataError:
        print("Error: The downloaded CSV file is empty.")
        return
    except Exception as e:
        print(f"An error occurred while loading M1 CSV: {e}")
        return

    validation_statuses = []
    print("Processing M1 records for validation...")
    
    for index, row in m1_df.iterrows():
        propnum_csv = row.get('propnum')
        spi_csv = row.get('spi')
        # property_pfi might not exist or have a different name, ensure to check actual column name
        pfi_csv = row.get('property_pfi', row.get('property pfi')) # Trying common variations

        rates_record = get_rates_data(propnum_csv, spi_csv, pfi_csv, sample_rates_data)
        status = validate_m1_row(row, rates_record) # Pass the original row with potentially spaced column names
        validation_statuses.append(status)
        
        current_propnum_str = str(row.get('propnum')).strip()
        # current_edit_code_str = str(row.get('edit_code')).strip().upper() # Moved this inside the if

        # Temporary print for debugging rows with propnum 170045.0
        # if current_propnum_str == "170045.0": # Condition removed for broader debug
        #     current_edit_code_str = str(row.get('edit_code')).strip().upper()
        #     print(f"DEBUG_PROPNUM_170045_FOUND @ index {index}:")
        #     print(f"  M1_propnum_val: '{row.get('propnum')}' (type: {type(row.get('propnum'))})")
        #     print(f"  M1_spi_val: '{row.get('spi')}' (type: {type(row.get('spi'))})")
        #     print(f"  M1_edit_code_val: '{row.get('edit_code')}' (Processed as: '{current_edit_code_str}')")
        #     print(f"  Rates Record Found for this row: {'Yes' if rates_record else 'No'}")
        #     if rates_record:
        #         print(f"  Rates Record propnum: {rates_record.get('propnum')}, spi: {rates_record.get('spi')}, Memo: {rates_record.get('Memo')}")
        #     print(f"  Generated Status for this row: {status}")

        # if index < 5 or index == 362: # Print for first 5 rows and specific index
        #      print(f"DEBUG_ROW_DATA @ index {index}: propnum_raw='{row.get('propnum')}', propnum_str_stripped='{str(row.get('propnum')).strip()}', edit_code='{row.get('edit_code')}'")

        # Removed specific debug prints for this run

        if (index + 1) % 100 == 0 or (index + 1) == len(m1_df): 
            print(f"Processed {index + 1}/{len(m1_df)} records...")

    m1_df['validation_status'] = validation_statuses
    print(f"\nValidation complete. Added 'validation_status' column.")

    try:
        m1_df.to_csv(output_filename, index=False)
        print(f"Successfully saved validated data to {output_filename}")
    except Exception as e:
        print(f"Error saving validated CSV: {e}")

if __name__ == "__main__":
    main()
