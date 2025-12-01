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
    Returns the Stock-to-Delivery 12-step process.
    This is the exact process that will be used - no tasks added or removed.
    Only descriptions will be customized for specific objectives.
    """
    return {
        "1. INFORMATION REQUIRED (1 day)": {
            "responsible": "Account Executive",
            "activities": "List out information that is required to kick off order-to-delivery process following order confirmed by sales team and product management team",
            "deliverable": "Required information list"
        },
        "2. SUPPLIER ENGAGEMENT & ORDER CONFIRMATION (3.5 days)": {
            "responsible": "Supply Chain Specialist",
            "activities": "Reach out to suppliers in Kenya, lock stock availability, get confirmations on stock and brand, confirm order and request Proforma invoice and deal price",
            "deliverable": "Supplier order confirmation and Proforma invoice"
        },
        "3. PRODUCT MANAGEMENT APPROVAL (0.5 day)": {
            "responsible": "Product Development Manager",
            "activities": "Get confirmation from Product Management team on the acceptance of the product",
            "deliverable": "Product acceptance confirmation"
        },
        "4. FOREIGN CURRENCY PERMIT APPLICATION (5 days)": {
            "responsible": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
            "activities": "Apply permit for foreign currency approval from the appropriate Bank and obtain permit",
            "deliverable": "Bank permit for foreign currency"
        },
        "5. SUPPLIER PAYMENT PROCESSING (5 days)": {
            "responsible": "Commercial & Finance Specialist (Consolidation and Kenya-Focused)",
            "activities": "Make payment for supplier and request to start documentation for export",
            "deliverable": "Payment confirmation"
        },
        "6. TRANSPORTATION LOGISTICS ARRANGEMENT (1 day)": {
            "responsible": "Kenyan operation specialist",
            "activities": "Look for the appropriate truck and provide details to supplier to be used for export documentation",
            "deliverable": "Transport arrangement confirmation"
        },
        "7. KENYA SIDE DISPATCH & CLEARANCE (2 days)": {
            "responsible": "Kenyan operation specialist",
            "activities": "Product will be dispatched at Kenya Moyale side and be cleared from Kenyan side",
            "deliverable": "Kenya border clearance documents"
        },
        "8. ETHIOPIAN CUSTOMS CLEARANCE (2 days)": {
            "responsible": "Kenyan operation specialist",
            "activities": "Ethiopian customs branch will do the clearing and process 1st payment based on permit value",
            "deliverable": "Ethiopian customs clearance"
        },
        "9. TAX REASSESSMENT & FINAL PAYMENT (0.5 day)": {
            "responsible": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
            "activities": "Tax reassessment and 2nd tax payment",
            "deliverable": "Final tax payment confirmation"
        },
        "10. PRODUCT LOADING & DISPATCH (0.5 day)": {
            "responsible": "Ethiopia Operation Specialist (Senior)",
            "activities": "Products will be loaded and dispatched",
            "deliverable": "Dispatch confirmation"
        },
        "11. TRANSPORT MONITORING (2 days)": {
            "responsible": "Ethiopia Operation Specialist (Senior)",
            "activities": "Follow trucks on the way to Ethiopia",
            "deliverable": "Transport status updates"
        },
        "12. FINAL DELIVERY TO WAREHOUSE (1 day)": {
            "responsible": "Tax Accounting & Admin Specialist (Ethiopia-Focused)",
            "activities": "Deliver products to warehouse",
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

