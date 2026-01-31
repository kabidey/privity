DEFAULT_EMAIL_TEMPLATES = {
    "welcome": {
        "key": "welcome",
        "name": "Welcome Email (Client)",
        "subject": "Welcome to Private Equity System",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Welcome to SMIFS Private Equity System</h2>
            <p>Dear {{client_name}},</p>
            <p>Your account has been created successfully!</p>
            <p>You can now participate in share booking transactions through our platform.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name"],
        "is_active": True
    },
    "client_approved": {
        "key": "client_approved",
        "name": "Client Approved",
        "subject": "Account Approved - Private Equity System",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">Account Approved ✓</h2>
            <p>Dear {{client_name}},</p>
            <p>Your account has been <strong style="color: #10b981;">APPROVED</strong> and is now active.</p>
            <p>Your OTC UCC: <strong>{{otc_ucc}}</strong></p>
            <p>You can now participate in share booking transactions.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "otc_ucc"],
        "is_active": True
    },
    "client_rejected": {
        "key": "client_rejected",
        "name": "Client Rejected",
        "subject": "Account Registration - Update Required",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #ef4444;">Account Registration Update</h2>
            <p>Dear {{client_name}},</p>
            <p>We regret to inform you that your account registration could not be approved at this time.</p>
            <p>This may be due to incomplete documentation or verification requirements.</p>
            <p>Please contact our team for more details and next steps.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name"],
        "is_active": True
    },
    "booking_created": {
        "key": "booking_created",
        "name": "Booking Created (Pending Approval)",
        "subject": "Booking Created - Pending Approval | {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #f59e0b;">Booking Order Created</h2>
            <p>Dear {{client_name}},</p>
            <p>A new booking order has been created and is pending internal approval.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Order ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}} - {{stock_name}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Status</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><span style="color: #f59e0b;">Pending Internal Approval</span></td>
                </tr>
            </table>
            
            <p style="color: #6b7280; font-size: 14px;">You will receive a confirmation request email once the booking is approved internally.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol", "stock_name", "quantity"],
        "is_active": True
    },
    "booking_confirmation_request": {
        "key": "booking_confirmation_request",
        "name": "Booking Confirmation Request",
        "subject": "Action Required: Confirm Booking - {{stock_symbol}} | {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">Booking Approved - Please Confirm ✓</h2>
            <p>Dear {{client_name}},</p>
            <p>Your booking order has been <strong style="color: #10b981;">APPROVED</strong> by PE Desk. Please confirm your acceptance to proceed.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Client OTC UCC</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{otc_ucc}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}} - {{stock_name}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Landing Price</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{buying_price}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Value</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{total_value}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Approved By</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{approved_by}} (PE Desk)</td>
                </tr>
            </table>
            
            <div style="margin: 30px 0; text-align: center;">
                <p style="margin-bottom: 20px; font-weight: bold;">Please confirm your booking:</p>
                <a href="{{accept_url}}" style="display: inline-block; background-color: #22c55e; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin-right: 10px; font-weight: bold;">✓ ACCEPT BOOKING</a>
                <a href="{{deny_url}}" style="display: inline-block; background-color: #ef4444; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">✗ DENY BOOKING</a>
            </div>
            
            <p style="color: #6b7280; font-size: 14px;">Please review and confirm this booking. If you accept, payment can be initiated. If you deny, the booking will be cancelled.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "otc_ucc", "stock_symbol", "stock_name", "quantity", "buying_price", "total_value", "approved_by", "accept_url", "deny_url"],
        "is_active": True
    },
    "booking_pending_loss_review": {
        "key": "booking_pending_loss_review",
        "name": "Booking Pending Loss Review",
        "subject": "Booking Approved - Pending Loss Review | {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #f59e0b;">Booking Approved - Pending Loss Review</h2>
            <p>Dear {{client_name}},</p>
            <p>Your booking order has been approved. However, since this is a loss transaction, it requires additional review. You will receive a confirmation request once fully approved.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Status</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><span style="color: #f59e0b;">Pending Loss Review</span></td>
                </tr>
            </table>
            
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol"],
        "is_active": True
    },
    "loss_booking_confirmation_request": {
        "key": "loss_booking_confirmation_request",
        "name": "Loss Booking Confirmation Request",
        "subject": "Action Required: Confirm Loss Booking - {{stock_symbol}} | {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">Booking Fully Approved - Please Confirm ✓</h2>
            <p>Dear {{client_name}},</p>
            <p>Your loss booking order has been <strong style="color: #10b981;">FULLY APPROVED</strong>. Please confirm your acceptance to proceed.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Landing Price</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{buying_price}}</td>
                </tr>
                <tr style="background-color: #fef3c7;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Selling Price</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{selling_price}} <span style="color: #dc2626;">(Loss Transaction)</span></td>
                </tr>
            </table>
            
            <div style="margin: 30px 0; text-align: center;">
                <p style="margin-bottom: 20px; font-weight: bold;">Please confirm your booking:</p>
                <a href="{{accept_url}}" style="display: inline-block; background-color: #22c55e; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin-right: 10px; font-weight: bold;">✓ ACCEPT BOOKING</a>
                <a href="{{deny_url}}" style="display: inline-block; background-color: #ef4444; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">✗ DENY BOOKING</a>
            </div>
            
            <p style="color: #6b7280; font-size: 14px;">This is a loss transaction booking. Please review carefully before confirming.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol", "quantity", "buying_price", "selling_price", "accept_url", "deny_url"],
        "is_active": True
    },
    "booking_status_updated": {
        "key": "booking_status_updated",
        "name": "Booking Status Updated",
        "subject": "Booking Status Updated - {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Booking Status Updated</h2>
            <p>Dear {{client_name}},</p>
            <p>Your booking <strong>{{booking_number}}</strong> status has been updated to: <strong style="color: #064E3B;">{{status}}</strong></p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "status"],
        "is_active": True
    },
    "payment_complete": {
        "key": "payment_complete",
        "name": "Client Payment Complete",
        "subject": "Payment Complete - Booking {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">Payment Complete ✓</h2>
            <p>Dear {{client_name}},</p>
            <p>We are pleased to confirm that full payment has been received for your booking:</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Amount</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{total_amount}}</td>
                </tr>
            </table>
            
            <div style="background-color: #d1fae5; border-left: 4px solid #10b981; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #065f46;"><strong>Your booking is now ready for DP transfer.</strong></p>
            </div>
            
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol", "quantity", "total_amount"],
        "is_active": True
    },
    "stock_transfer_complete": {
        "key": "stock_transfer_complete",
        "name": "Stock Transfer Completed",
        "subject": "Stock Transfer Completed - {{stock_symbol}} | {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">✓ Stock Transfer Completed</h2>
            <p>Dear {{client_name}},</p>
            <p>We are pleased to inform you that your stock has been successfully transferred to your Demat account.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #064E3B; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Transfer Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; width: 40%;"><strong>Booking Reference</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock Symbol</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock Name</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_name}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>ISIN Number</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{isin_number}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity Transferred</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Your DP ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong style="color: #064E3B;">{{dp_id}}</strong></td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Transfer Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{transfer_date}}</td>
                </tr>
            </table>
            
            <div style="background-color: #d1fae5; border-left: 4px solid #10b981; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #065f46;"><strong>Note:</strong> Please verify the credit in your Demat account. The shares should reflect within 1-2 working days.</p>
            </div>
            
            <p>If you have any questions, please contact us.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol", "stock_name", "isin_number", "quantity", "dp_id", "transfer_date"],
        "is_active": True
    },
    "purchase_order_created": {
        "key": "purchase_order_created",
        "name": "Purchase Order Created (Vendor)",
        "subject": "Purchase Order Confirmation - {{stock_symbol}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Purchase Order Confirmation</h2>
            <p>Dear {{vendor_name}},</p>
            <p>A purchase order has been created for your stock.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Price per Unit</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{price_per_unit}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Amount</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{total_amount}}</td>
                </tr>
            </table>
            
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["vendor_name", "stock_symbol", "quantity", "price_per_unit", "total_amount"],
        "is_active": True
    },
    "vendor_payment_received": {
        "key": "vendor_payment_received",
        "name": "Vendor Payment Received",
        "subject": "Payment Received - {{stock_symbol}} Purchase | ₹{{payment_amount}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">Payment Received</h2>
            <p>Dear {{vendor_name}},</p>
            <p>We are pleased to inform you that a payment has been processed for your stock purchase.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #064E3B; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Payment Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; width: 40%;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}} - {{stock_name}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Purchase Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Purchase Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{purchase_date}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Purchase Amount</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{total_amount}}</td>
                </tr>
                <tr style="background-color: #d1fae5;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>This Payment</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong style="color: #10b981;">₹{{payment_amount}}</strong></td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Paid Till Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{total_paid}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Balance Remaining</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{remaining_balance}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Payment Status</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>{{payment_status}}</strong></td>
                </tr>
            </table>
            
            <p>If you have any questions regarding this payment, please contact us.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["vendor_name", "stock_symbol", "stock_name", "quantity", "purchase_date", "total_amount", "payment_amount", "total_paid", "remaining_balance", "payment_status"],
        "is_active": True
    },
    "password_otp": {
        "key": "password_otp",
        "name": "Password Reset OTP",
        "subject": "Password Reset OTP - Private Equity System",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Password Reset Request</h2>
            <p>Dear {{user_name}},</p>
            <p>Your OTP for password reset is:</p>
            <div style="background: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
                <h1 style="color: #064E3B; letter-spacing: 5px; margin: 0;">{{otp}}</h1>
            </div>
            <p>This OTP is valid for <strong>{{expiry_minutes}} minutes</strong>.</p>
            <p style="color: #6b7280; font-size: 14px;">If you did not request this password reset, please ignore this email.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["user_name", "otp", "expiry_minutes"],
        "is_active": True
    },
    "user_created": {
        "key": "user_created",
        "name": "User Account Created",
        "subject": "Welcome to Private Equity System - Account Created",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Welcome to SMIFS Private Equity System</h2>
            <p>Dear {{user_name}},</p>
            <p>Your staff account has been created successfully!</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Email</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{email}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Role</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{role_name}}</td>
                </tr>
            </table>
            
            <p>You can now log in to the system using your credentials.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["user_name", "email", "role_name"],
        "is_active": True
    },
    "refund_completed": {
        "key": "refund_completed",
        "name": "Refund Completed",
        "subject": "Refund Processed - Booking {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Refund Processed Successfully</h2>
            <p>Dear {{client_name}},</p>
            <p>We are pleased to inform you that your refund has been processed successfully.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #064E3B; color: white;">
                    <th style="padding: 10px; text-align: left;" colspan="2">Refund Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking Number</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Refund Amount</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong style="color: #059669;">₹{{refund_amount}}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Reference Number</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{reference_number}}</td>
                </tr>
            </table>
            
            <p>The refund amount has been credited to your registered bank account. Please allow 2-3 business days for the amount to reflect in your account.</p>
            <p>If you have any questions regarding this refund, please contact us.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol", "refund_amount", "reference_number"],
        "is_active": True
    },
    "rp_deal_notification": {
        "key": "rp_deal_notification",
        "name": "RP Deal Notification",
        "subject": "Revenue Booked - Booking {{booking_number}} | SMIFS PE",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">✓ New Revenue Booked</h2>
            <p>Dear {{rp_name}},</p>
            <p>We are pleased to inform you that a stock transfer has been completed for a booking you referred. Your commission has been booked.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #064E3B; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Deal Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; width: 40%;"><strong>Your RP Code</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-family: monospace;">{{rp_code}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking Reference</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Client Name</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{client_name}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}} - {{stock_name}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Transfer Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{transfer_date}}</td>
                </tr>
            </table>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #7c3aed; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Your Commission</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Deal Profit</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{profit}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Your Share</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{revenue_share_percent}}%</td>
                </tr>
                <tr style="background-color: #d1fae5;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Commission Amount</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong style="color: #059669; font-size: 18px;">₹{{payment_amount}}</strong></td>
                </tr>
            </table>
            
            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #92400e;"><strong>Note:</strong> Your commission is now pending and will be processed as per our payment cycle.</p>
            </div>
            
            <p>Thank you for your continued partnership!</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["rp_name", "rp_code", "booking_number", "client_name", "stock_symbol", "stock_name", "quantity", "transfer_date", "profit", "revenue_share_percent", "payment_amount"],
        "is_active": True
    },
    "rp_approval_notification": {
        "key": "rp_approval_notification",
        "name": "RP Approval Notification",
        "subject": "Welcome! Your Referral Partner Application is Approved | SMIFS PE",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">✓ Application Approved</h2>
            <p>Dear {{rp_name}},</p>
            <p>We are pleased to inform you that your Referral Partner application has been <strong style="color: #10b981;">APPROVED</strong>.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #064E3B; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Your RP Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; width: 40%;"><strong>Your RP Code</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-family: monospace; font-size: 16px; color: #059669;"><strong>{{rp_code}}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Name</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{rp_name}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>PAN Number</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{pan_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Approved By</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{approved_by}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Approval Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{approval_date}}</td>
                </tr>
            </table>
            
            <div style="background-color: #d1fae5; border-left: 4px solid #10b981; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #065f46;"><strong>What's Next?</strong> You can now refer clients and earn commissions on successful bookings. Share your RP code <strong>{{rp_code}}</strong> with potential clients.</p>
            </div>
            
            <p>Thank you for partnering with us!</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["rp_name", "rp_code", "pan_number", "approved_by", "approval_date"],
        "is_active": True
    },
    "rp_rejection_notification": {
        "key": "rp_rejection_notification",
        "name": "RP Rejection Notification",
        "subject": "Referral Partner Application Update | SMIFS PE",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc2626;">Application Not Approved</h2>
            <p>Dear {{rp_name}},</p>
            <p>We regret to inform you that your Referral Partner application has not been approved at this time.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #7f1d1d; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Application Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; width: 40%;"><strong>Application Code</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-family: monospace;">{{rp_code}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Name</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{rp_name}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>PAN Number</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{pan_number}}</td>
                </tr>
            </table>
            
            <div style="background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #991b1b;"><strong>Reason for Rejection:</strong></p>
                <p style="margin: 8px 0 0 0; color: #7f1d1d;">{{rejection_reason}}</p>
            </div>
            
            <p>If you believe this decision was made in error or would like to re-apply with corrected information, please contact our PE Desk.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["rp_name", "rp_code", "pan_number", "rejection_reason"],
        "is_active": True
    },
    "corporate_action_notification": {
        "key": "corporate_action_notification",
        "name": "Corporate Action Notification",
        "subject": "Corporate Action Notice - {{action_type}} for {{stock_symbol}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Corporate Action Notification</h2>
            <p>Dear {{client_name}},</p>
            <p>We would like to inform you about an upcoming corporate action on one of your holdings:</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #064E3B; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Corporate Action Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; width: 40%;"><strong>Stock Symbol</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock Name</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_name}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Action Type</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><span style="color: #059669; font-weight: bold;">{{action_type}}</span></td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Record Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{record_date}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Ex Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{ex_date}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Your Holdings</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>{{quantity}} shares</strong></td>
                </tr>
            </table>
            
            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #92400e;"><strong>Details:</strong> {{description}}</p>
            </div>
            
            <p style="color: #6b7280; font-size: 14px;">The corporate action will be processed as per the record date. Your portfolio will be updated accordingly.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "stock_symbol", "stock_name", "action_type", "record_date", "ex_date", "quantity", "description"],
        "is_active": True
    },
    "contract_note": {
        "key": "contract_note",
        "name": "Contract Note Email",
        "subject": "Contract Note - {{contract_note_number}} | {{stock_symbol}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Contract Note</h2>
            <p>Dear {{client_name}},</p>
            <p>Please find attached your Contract Note for the following transaction:</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #064E3B; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Transaction Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; width: 40%;"><strong>Contract Note Number</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-family: monospace;">{{contract_note_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking Reference</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}} - {{stock_name}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}} shares</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Trade Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{trade_date}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Amount</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong style="color: #059669;">₹{{total_amount}}</strong></td>
                </tr>
            </table>
            
            <div style="background-color: #d1fae5; border-left: 4px solid #10b981; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #065f46;">📎 <strong>The Contract Note PDF is attached to this email.</strong></p>
            </div>
            
            <p style="color: #6b7280; font-size: 14px;">Please keep this document for your records. If you have any queries, please contact our PE Desk.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "contract_note_number", "booking_number", "stock_symbol", "stock_name", "quantity", "trade_date", "total_amount"],
        "is_active": True
    },
    "bp_login_otp": {
        "key": "bp_login_otp",
        "name": "Business Partner Login OTP",
        "subject": "Your Privity Login OTP",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Login Verification Code</h2>
            <p>Dear {{bp_name}},</p>
            <p>Your one-time password (OTP) for logging into the Privity Business Partner Portal is:</p>
            <div style="background: linear-gradient(135deg, #10b981, #059669); padding: 30px; text-align: center; margin: 20px 0; border-radius: 12px;">
                <h1 style="color: white; letter-spacing: 10px; margin: 0; font-size: 36px;">{{otp}}</h1>
            </div>
            <p><strong>This OTP is valid for {{expiry_minutes}} minutes.</strong></p>
            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #92400e;"><strong>Security Notice:</strong> Do not share this OTP with anyone. SMIFS staff will never ask for your OTP.</p>
            </div>
            <p style="color: #6b7280; font-size: 14px;">If you didn't request this OTP, please ignore this email.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["bp_name", "otp", "expiry_minutes"],
        "is_active": True
    },
    "payment_request": {
        "key": "payment_request",
        "name": "Payment Request (Booking Approved)",
        "subject": "Payment Request - Booking {{booking_number}} | {{stock_symbol}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; background: #ffffff;">
            <div style="background: linear-gradient(135deg, #10b981, #059669); padding: 25px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px;">Payment Request</h1>
                <p style="color: #d1fae5; margin: 10px 0 0 0; font-size: 14px;">Booking Reference: {{booking_number}}</p>
            </div>
            
            <div style="padding: 30px;">
                <p style="font-size: 16px; color: #374151;">Dear <strong>{{client_name}}</strong>,</p>
                
                <p style="color: #4b5563; line-height: 1.6;">
                    Your booking has been approved by our PE Desk. Please find below the payment details for completing your investment.
                </p>
                
                <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #e5e7eb;">
                    <h3 style="color: #111827; margin: 0 0 15px 0; font-size: 16px;">📋 Booking Summary</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280; width: 40%;">Stock:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600;">{{stock_symbol}} - {{stock_name}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280;">Quantity:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600;">{{quantity}} shares</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280;">Price per Share:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600;">₹{{price_per_share}}</td>
                        </tr>
                        <tr style="background: #ecfdf5;">
                            <td style="padding: 15px 10px; color: #065f46; font-weight: bold; font-size: 18px;">Total Amount Payable:</td>
                            <td style="padding: 15px 10px; color: #065f46; font-weight: bold; font-size: 22px;">₹{{total_amount}}</td>
                        </tr>
                    </table>
                </div>
                
                <div style="background: #eff6ff; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #bfdbfe;">
                    <h3 style="color: #1e40af; margin: 0 0 15px 0; font-size: 16px;">🏦 Bank Account Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280; width: 40%;">Beneficiary Name:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600;">{{company_name}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280;">Bank Name:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600;">{{bank_name}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280;">Account Number:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600; font-family: monospace;">{{bank_account}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280;">IFSC Code:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600; font-family: monospace;">{{bank_ifsc}}</td>
                        </tr>
                    </table>
                </div>
                
                <div style="background: #fef3c7; border-radius: 12px; padding: 15px; margin: 25px 0; border: 1px solid #fcd34d;">
                    <p style="color: #92400e; margin: 0; font-size: 14px;"><strong>⚠️ Important:</strong> Please mention Booking Reference <strong>{{booking_number}}</strong> in the payment remarks.</p>
                </div>
                
                <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
            </div>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol", "stock_name", "quantity", "price_per_share", "total_amount", "company_name", "bank_name", "bank_account", "bank_ifsc"],
        "is_active": True
    },
    "stock_transfer_request": {
        "key": "stock_transfer_request",
        "name": "Stock Transfer Request (Vendor)",
        "subject": "Stock Transfer Request - {{stock_symbol}} | {{purchase_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; background: #ffffff;">
            <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); padding: 25px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px;">Stock Transfer Request</h1>
                <p style="color: #bfdbfe; margin: 10px 0 0 0; font-size: 14px;">Purchase Reference: {{purchase_number}}</p>
            </div>
            
            <div style="padding: 30px;">
                <p style="font-size: 16px; color: #374151;">Dear <strong>{{vendor_name}}</strong>,</p>
                
                <p style="color: #4b5563; line-height: 1.6;">
                    We are pleased to inform you that the <strong>full payment</strong> for your stock purchase order has been completed. 
                    We kindly request you to <strong>initiate the stock transfer immediately</strong>.
                </p>
                
                <div style="background: #ecfdf5; border-radius: 12px; padding: 20px; margin: 25px 0; border: 2px solid #10b981;">
                    <h3 style="color: #065f46; margin: 0 0 15px 0; font-size: 16px;">✓ Payment Confirmation</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280; width: 40%;">Total Amount Paid:</td>
                            <td style="padding: 10px 0; color: #065f46; font-weight: bold; font-size: 20px;">₹{{total_paid}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280;">Payment Date:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600;">{{payment_date}}</td>
                        </tr>
                    </table>
                </div>
                
                <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #e5e7eb;">
                    <h3 style="color: #111827; margin: 0 0 15px 0; font-size: 16px;">📋 Stock Transfer Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280; width: 40%;">Stock:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600;">{{stock_symbol}} - {{stock_name}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280;">Quantity to Transfer:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600; font-size: 18px;">{{quantity}} shares</td>
                        </tr>
                    </table>
                </div>
                
                <div style="background: #eff6ff; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #bfdbfe;">
                    <h3 style="color: #1e40af; margin: 0 0 15px 0; font-size: 16px;">🏦 Transfer To (Our DP Details)</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280; width: 40%;">Beneficiary:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600;">{{company_name}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280;">CDSL DP ID:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600; font-family: monospace;">{{cdsl_dp_id}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280;">NSDL DP ID:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600; font-family: monospace;">{{nsdl_dp_id}}</td>
                        </tr>
                    </table>
                </div>
                
                <div style="background: #fef2f2; border-radius: 12px; padding: 20px; margin: 25px 0; border: 2px solid #ef4444;">
                    <h3 style="color: #991b1b; margin: 0 0 10px 0; font-size: 16px;">⚠️ Immediate Action Required</h3>
                    <p style="color: #7f1d1d; margin: 0; line-height: 1.6;">
                        As the full payment has been completed, we kindly request you to <strong>initiate the stock transfer immediately</strong>.
                    </p>
                </div>
                
                <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
            </div>
        </div>
        """,
        "variables": ["vendor_name", "purchase_number", "stock_symbol", "stock_name", "quantity", "total_paid", "payment_date", "company_name", "cdsl_dp_id", "nsdl_dp_id"],
        "is_active": True
    },
    "stock_transferred": {
        "key": "stock_transferred",
        "name": "Stock Transfer Completed (Client)",
        "subject": "Stock Transfer Completed - {{stock_symbol}} | Booking {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; background: #ffffff;">
            <div style="background: linear-gradient(135deg, #10b981, #059669); padding: 25px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px;">Stock Transfer Completed</h1>
                <p style="color: #d1fae5; margin: 10px 0 0 0; font-size: 14px;">Booking Reference: {{booking_number}}</p>
            </div>
            
            <div style="padding: 30px;">
                <p style="font-size: 16px; color: #374151;">Dear <strong>{{client_name}}</strong>,</p>
                
                <p style="color: #4b5563; line-height: 1.6;">
                    We are pleased to inform you that your stock transfer has been <strong>successfully completed</strong>. 
                    The shares have been transferred to your demat account.
                </p>
                
                <div style="background: #ecfdf5; border-radius: 12px; padding: 20px; margin: 25px 0; border: 2px solid #10b981; text-align: center;">
                    <div style="font-size: 48px; margin-bottom: 10px;">✓</div>
                    <h2 style="color: #065f46; margin: 0 0 10px 0;">Transfer Successful</h2>
                    <p style="color: #047857; margin: 0; font-size: 14px;">
                        Your shares will reflect in your demat account by <strong>{{t2_date}}</strong> (T+2 settlement)
                    </p>
                </div>
                
                <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin: 25px 0; border: 1px solid #e5e7eb;">
                    <h3 style="color: #111827; margin: 0 0 15px 0; font-size: 16px;">📋 Transfer Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280; width: 40%;">Stock:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600;">{{stock_symbol}} - {{stock_name}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280;">Quantity Transferred:</td>
                            <td style="padding: 10px 0; color: #111827; font-weight: 600; font-size: 18px;">{{quantity}} shares</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280;">Transfer Mode:</td>
                            <td style="padding: 10px 0;">
                                <span style="background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 14px;">{{dp_type}}</span>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #6b7280;">Transfer Date:</td>
                            <td style="padding: 10px 0; color: #111827;">{{transfer_date}}</td>
                        </tr>
                    </table>
                </div>
                
                <div style="background: #fefce8; border-radius: 12px; padding: 15px; margin: 25px 0; border: 1px solid #fcd34d;">
                    <p style="color: #854d0e; margin: 0; font-size: 14px;">
                        <strong>Need Help?</strong> If you don't see the shares in your account after {{t2_date}}, 
                        please contact our PE Desk with your booking reference: <strong>{{booking_number}}</strong>
                    </p>
                </div>
                
                <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
            </div>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol", "stock_name", "quantity", "dp_type", "transfer_date", "t2_date"],
        "is_active": True
    }
}
