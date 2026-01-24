"""
Services package
"""
from services.email_service import (
    send_email, 
    send_templated_email, 
    send_otp_email, 
    generate_otp,
    get_email_template,
    render_template,
    init_email_templates
)
from services.analytics_service import (
    get_analytics_summary,
    get_stock_performance,
    get_employee_performance,
    get_daily_trend,
    get_client_growth,
    get_sector_distribution
)
