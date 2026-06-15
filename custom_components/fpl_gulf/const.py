DOMAIN = "fpl_gulf"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_ACCOUNT_NUMBER = "account_number"

COGNITO_URL = "https://cognito-idp.us-east-1.amazonaws.com"
COGNITO_CLIENT_ID = "1dt9rk4cta0ts8obgrs2sef4s3"

# Verified operational data routes
URL_REM_ACCOUNT_SUMMARY = "https://www.fpl.com/cs/gulf/ssp/v1/rem/resources/account/{account}/account-summary"
URL_ACCOUNT_LITE_INFO = "https://www.fpl.com/cs/customer/v3/accountservices/resources/accounts/{account}/lite-info"
URL_BILLING_HISTORY = "https://www.fpl.com/cs/customer/v3/account-summary/resources/accounts/bill-histories/{account}"
URL_METER_INSTALLATIONS = "https://www.fpl.com/cs/customer/v3/account-summary/resources/accounts/{account}/installations"
URL_MONTHLY_USAGE = "https://www.fpl.com/cs/gulf/ssp/v1/accountservices/account/{account}/monthlyUsage?contractId={contract_id}"
URL_USAGE_COMPARISON = "https://www.fpl.com/cs/gulf/ssp/v1/rem/resources/customer/accounts/{account}/usage-comparison?contractId={contract_id}"
URL_DISAGGREGATION = "https://www.fpl.com/cs/gulf/ssp/v1/rem/resources/customer/accounts/{account}/get-disagg"
URL_LIVE_ACCOUNT_SUMMARY = "https://www.fpl.com/cs/gulf/ssp/v1/accountservices/account/{account}/accountSummary?balance=n"