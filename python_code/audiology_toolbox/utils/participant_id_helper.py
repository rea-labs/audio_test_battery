"""
Helper function to get participant ID from user.

Add this to your test scripts to prompt for participant ID.
"""

def get_participant_id(default="P001"):
    """
    Prompt user for participant ID with validation.
    
    Args:
        default: Default participant ID if user presses Enter
        
    Returns:
        str: Valid participant ID
    """
    while True:
        pid = input(f"\nEnter Participant ID [{default}]: ").strip()
        
        if not pid:
            pid = default
            print(f"Using default: {pid}")
            return pid
        
        # Basic validation
        if len(pid) < 2:
            print("⚠ Participant ID too short. Please use at least 2 characters.")
            continue
        
        # Optional: Check format (e.g., P001, P002, etc.)
        # Uncomment if you want to enforce a specific format:
        # if not pid[0].isalpha() or not pid[1:].isdigit():
        #     print("⚠ Format should be letter + numbers (e.g., P001, P002)")
        #     continue
        
        return pid


# Example usage in test script:
if __name__ == "__main__":
    # At the start of your test script
    participant_id = get_participant_id(default="P001")
    
    print(f"\nRunning test for participant: {participant_id}")
    
    # Then use it when creating paradigm
    from paradigms.paradigm_pta import ParadigmPTA
    
    pta = ParadigmPTA(params, participant_id=participant_id)
    pta.main()
