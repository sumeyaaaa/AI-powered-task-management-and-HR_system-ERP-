"""
Predefined Process Templates Registry

This module contains all predefined process templates that can be used for task generation.
To add a new predefined process:
1. Add the process definition to PREDEFINED_PROCESSES dictionary
2. The system will automatically use it when template matches the key
"""

def get_predefined_processes_registry():
    """]
    Returns registry of all predefined processes.
    Each process is a dictionary with step keys and step data.
    
    Returns:
        dict: Dictionary of process templates
    """
    return {
        'order_to_delivery': get_order_to_delivery_process(),
        'stock_to_delivery': get_stock_to_delivery_process(),
        'employee_onboarding': get_employee_onboarding_process(),
        # Add more predefined processes here:
        # 'new_process_name': get_new_process_function(),
    }

def get_order_to_delivery_process():
    """
    Returns the Order-to-Delivery 13-step process.
    This is the exact process that will be used - no tasks added or removed.
    Only descriptions will be customized for specific objectives.
    """
    return {
        "1. FINALIZE DEAL DOCUMENTATION (1 day)": {
            "responsible": "Account Executive",
            "activities": "Complete agreement, Proforma Invoice (PI), and other commercial terms",
            "deliverable": "Signed PI and commercial agreement"
        },
        "2. SUPPLIER STOCK ORDER CONFIRMATION (1 day)": {
            "responsible": "Supply Chain Specialist", 
            "activities": "Contact Kenya suppliers, verify stock availability, reserve inventory, obtain written confirmation, formal order placement, request proforma invoice and final pricing",
            "deliverable": "Supplier order confirmation"
        },
        "3. PRODUCT MANAGEMENT APPROVAL (0.5 day)": {
            "responsible": "Product Development Manager",
            "activities": "Validate product specifications meet quality standards",
            "deliverable": "Product acceptance confirmation"
        },
        "4. FOREIGN CURRENCY PERMIT APPLICATION (5 days)": {
            "responsible": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
            "activities": "Apply for foreign currency approval from appropriate bank, obtain permit",
            "deliverable": "Bank permit for foreign currency"
        },
        "5. SUPPLIER PAYMENT PROCESSING (5 days)": {
            "responsible": "Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
            "activities": "Process payment to supplier, request export documentation initiation",
            "deliverable": "Payment confirmation and supplier acknowledgment"
        },
        "6. TRANSPORTATION LOGISTICS ARRANGEMENT (1 day)": {
            "responsible": "Kenyan operation specialist", 
            "activities": "Identify appropriate truck, coordinate with supplier for export documentation",
            "deliverable": "Transport arrangement confirmation and supplier export documentation"
        },
        "7. KENYA SIDE DISPATCH & CLEARANCE (2 days)": {
            "responsible": "Kenyan operation specialist",
            "activities": "Coordinate product dispatch from Kenya Moyale side, complete Kenyan customs clearance",
            "deliverable": "Kenya border clearance documents"
        },
        "8. ETHIOPIAN CUSTOMS CLEARANCE (2 days)": {
            "responsible": "Ethiopian Operation Specialist",
            "activities": "Handle Ethiopian customs clearance, process 1st payment based on permit value",
            "deliverable": "Ethiopian customs clearance certificate"
        },
        "9. TAX REASSESSMENT & FINAL PAYMENT (0.5 day)": {
            "responsible": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
            "activities": "Complete tax reassessment, process 2nd tax payment",
            "deliverable": "Final tax payment confirmation"
        },
        "10. PRODUCT LOADING & DISPATCH (0.5 day)": {
            "responsible": "Ethiopian Operation Specialist",
            "activities": "Supervise product loading, coordinate dispatch to final destination", 
            "deliverable": "Dispatch confirmation"
        },
        "11. TRANSPORT MONITORING (2 days)": {
            "responsible": "Ethiopian Operation Specialist",
            "activities": "Track truck movement, coordinate with transport provider",
            "deliverable": "Regular transport status updates"
        },
        "12. FINAL DELIVERY & WAREHOUSE HANDOVER (1 day)": {
            "responsible": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
            "activities": "Coordinate final delivery to customer warehouse, complete handover",
            "deliverable": "Customer delivery confirmation and signed receipt"
        },
        "13. POST-DELIVERY DOCUMENTATION & SETTLEMENT (1 day)": {
            "responsible": "Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
            "activities": "Complete all financial settlements, document archiving, lesson learned",
            "deliverable": "Closed order file and settlement confirmation"
        }
    }

def get_stock_to_delivery_process():
    """
    Returns the Stock-to-Delivery 13-step process.
    This is the exact process that will be used - no tasks added or removed.
    Only descriptions will be customized for specific objectives.
    """
    return {
        "1. REACH OUT TO SUPPLIERS IN KENYA AND LOCK STOCK AVAILABILITY (2 days)": {
            "responsible": "Supply Chain Specialist",
            "activities": "Contact Kenya suppliers and reserve inventory",
            "deliverable": "Stock availability confirmation"
        },
        "2. GET CONFIRMATIONS FROM KENYA SUPPLIER ON STOCK AVAILABILITY AND BRAND (1 day)": {
            "responsible": "Supply Chain Specialist", 
            "activities": "Verify stock availability and obtain written confirmation",
            "deliverable": "Supplier stock confirmation"
        },
        "3. GET CONFIRMATION FOR PRODUCT MANAGEMENT TEAM ON THE ACCEPTANCE OF THE PRODUCT (0.5 day)": {
            "responsible": "Supply Chain Specialist",
            "activities": "Validate product specifications meet quality standards",
            "deliverable": "Product acceptance confirmation"
        },
        "4. CONFIRM ORDER TO KENYA SUPPLIER AND REQUEST FOR PROFORMA AND DEAL PRICE (0.5 day)": {
            "responsible": "Supply Chain Specialist",
            "activities": "Formal order placement and request proforma invoice",
            "deliverable": "Proforma invoice and final pricing"
        },
        "5. APPLY PERMIT FOR FOREIGN CURRENCY APPROVAL FROM THE APPROPRIATE BANK AND GET PERMIT (5 days)": {
            "responsible": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
            "activities": "Apply for foreign currency approval from bank",
            "deliverable": "Bank permit for foreign currency"
        },
        "6. MAKE PAYMENT FOR SUPPLIER AND REQUEST TO START DOCUMENTATION FOR EXPORT (5 days)": {
            "responsible": "Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
            "activities": "Process payment to supplier and request export documentation",
            "deliverable": "Payment confirmation"
        },
        "7. LOOK FOR THE APPROPRIATE TRUCK AND PROVIDE FOR SUPPLIER TO BE USED FOR EXPORT DOCUMENTATION (1 day)": {
            "responsible": "Kenyan operation specialist", 
            "activities": "Identify appropriate truck and coordinate with supplier",
            "deliverable": "Transport arrangement confirmation"
        },
        "8. PRODUCT WILL BE DISPATCHED AT KENYA MOYALE SIDE AND BE CLEARED FROM KENYAN SIDE (2 days)": {
            "responsible": "Kenyan operation specialist",
            "activities": "Coordinate product dispatch and Kenyan customs clearance",
            "deliverable": "Kenya border clearance documents"
        },
        "9. ETHIOPIAN CUSTOMS BRANCH WILL DO THE CLEARING PAY 1ST PAYMENT BASED ON PERMIT VALUE (2 days)": {
            "responsible": "Kenyan operation specialist",
            "activities": "Handle Ethiopian customs clearance and process 1st payment",
            "deliverable": "Ethiopian customs clearance"
        },
        "10. TAX REASSESSMENT AND 2ND TAX (0.5 day)": {
            "responsible": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
            "activities": "Complete tax reassessment and process 2nd tax payment",
            "deliverable": "Final tax payment confirmation"
        },
        "11. PRODUCTS WILL BE LOADED AND DISPATCHED (0.5 day)": {
            "responsible": "Ethiopia Operation Specialist (Senior)",
            "activities": "Supervise product loading and coordinate dispatch", 
            "deliverable": "Dispatch confirmation"
        },
        "12. FOLLOW TRUCKS ON THE WAY TO ETHIOPIA (2 days)": {
            "responsible": "Ethiopia Operation Specialist (Senior)",
            "activities": "Track truck movement and coordinate with transport provider",
            "deliverable": "Transport status updates"
        },
        "13. DELIVER TO WAREHOUSE (1 day)": {
            "responsible": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
            "activities": "Coordinate final delivery to warehouse",
            "deliverable": "Warehouse delivery confirmation"
        }
    }

def get_employee_onboarding_process():
    """
    Returns the Employee Onboarding 8-step process.
    This is the exact process that will be used - no tasks added or removed.
    Only descriptions will be customized for specific objectives.
    """
    return {
        "1. PRE-ONBOARDING PREPARATION (1 day)": {
            "responsible": "HR Manager",
            "activities": "Prepare welcome package, set up workstation, create email account, prepare access cards and badges",
            "deliverable": "Workstation ready and access credentials prepared"
        },
        "2. FIRST DAY WELCOME & ORIENTATION (1 day)": {
            "responsible": "HR Manager",
            "activities": "Welcome meeting, company introduction, tour of facilities, introduction to team members",
            "deliverable": "Employee oriented and introduced to team"
        },
        "3. DOCUMENTATION & COMPLIANCE (1 day)": {
            "responsible": "HR Specialist",
            "activities": "Complete employment contract, tax forms, insurance enrollment, policy acknowledgments",
            "deliverable": "All legal and compliance documents signed"
        },
        "4. IT SETUP & SYSTEM ACCESS (0.5 day)": {
            "responsible": "IT Support Specialist",
            "activities": "Configure laptop/computer, install required software, set up system accounts, provide login credentials",
            "deliverable": "IT systems configured and accessible"
        },
        "5. ROLE-SPECIFIC TRAINING (3 days)": {
            "responsible": "Department Manager",
            "activities": "Job-specific training, process documentation review, shadow experienced team member, initial task assignment",
            "deliverable": "Employee trained on role responsibilities"
        },
        "6. COMPANY POLICIES & CULTURE (1 day)": {
            "responsible": "HR Manager",
            "activities": "Review employee handbook, code of conduct, safety procedures, company values and culture",
            "deliverable": "Employee understands company policies"
        },
        "7. MENTOR ASSIGNMENT & BUDDY SYSTEM (0.5 day)": {
            "responsible": "Department Manager",
            "activities": "Assign mentor/buddy, schedule regular check-ins, set up support channels",
            "deliverable": "Mentor assigned and support structure established"
        },
        "8. 30-DAY CHECK-IN & FEEDBACK (1 day)": {
            "responsible": "HR Manager",
            "activities": "Conduct 30-day review meeting, gather feedback, address concerns, adjust onboarding plan if needed",
            "deliverable": "Onboarding feedback collected and action plan updated"
        }
    }

# Example: How to add a new predefined process
# def get_new_process_template():
#     """Returns a new predefined process template"""
#     return {
#         "Step 1": {
#             "responsible": "Role Name",
#             "activities": "What needs to be done",
#             "deliverable": "Expected output"
#         },
#         # ... more steps
#     }
# Then add to PREDEFINED_PROCESSES: 'new_process_name': get_new_process_template()

