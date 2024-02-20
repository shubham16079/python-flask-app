from flask import Flask, render_template,session, redirect, url_for,request,json,jsonify
from db import get_db, close_db
from datetime import datetime

app = Flask(__name__)
PROJECT_SESSION_USER = 'user'
DB_PREFIX = 'flask'
DB_BILLING_PREFIX = 'flask_billing'

# @app.before_request
# def check_session():
#     if hasattr(g, 'ajaxcall') and g.ajaxcall:
#         # Assume g.ajaxcall is a global variable for AJAX calls
#         if PROJECT_SESSION_USER not in session or not session[PROJECT_SESSION_USER]:
#             g.ajaxcall = False
#             return {'error': 'Your Telgoo5 session has timed out. Please sign in again to continue.'}, 401

#     elif PROJECT_SESSION_USER not in session or not session[PROJECT_SESSION_USER]:
#         return redirect(url_for('index'))
@app.route('/')
def base():
    return render_template('base.html')
    
@app.route('/view-email-notification', methods=['GET','POST'])
def view_email_notification():
    cursor = get_db().cursor()
    page = int(request.form['page']) if request.form and request.form['page'] else 0
    disp_rec = 10
    if page is not None and page >= 0:
        start = page * disp_rec
    else:
        page = 0
        start = 0
        
    sms_notification = request.args.get('sms_notification')
    if sms_notification == 'Search':
        page = 0
        start = 0
    SHOW_OPTION_PLAN_TYPE = "LIFELINE,ACP"
    templateNameWhere = selected_template = ''
    if request.method == 'POST' and 'template_name' in request.form and request.form['template_name']:
        selected_template = request.form['template_name']
        templateNameWhere = " and event_id = '" + request.form['template_name'] + "'"


    carrierWhere = selected_carrier =  ''
    if request.method == 'POST' and 'carrier_select[]' in request.form and request.form.getlist('carrier_select[]'):
        selected_carrier = request.form.getlist('carrier_select[]')
        carrier_select = "','".join(request.form.getlist('carrier_select[]'))
        carrierWhere = " and carrier_code in ('" + carrier_select + "')"

    stateWhere = selected_states =  ''
    if request.method == 'POST' and 'state_list[]' in request.form and request.form.getlist('state_list[]'):
        selected_states = request.form.getlist('state_list[]')
        state_data = '|'.join(request.form.getlist('state_list[]'))
        stateWhere = ' AND CONCAT(",", state, ",") REGEXP ",(' + state_data + '),"'        

    planTypeWhere = template_plan_type =  ''
    if request.method == 'POST' and 'template_plan_type' in request.form and request.form['template_plan_type']:
        template_plan_type = request.form['template_plan_type']
        planTypeWhere = " AND plan_type = '" + template_plan_type + "'"
    
    count_query = f"""SELECT COUNT(*) as total_count FROM {DB_PREFIX}.tbl_email_templates as EWD 
                    LEFT JOIN {DB_PREFIX}.event_list as EL ON EWD.event_id = EL.id 
                    WHERE template_type='EMAIL' and EL.status = 'Y' {carrierWhere} {templateNameWhere} {stateWhere} {planTypeWhere}"""


    Sql = f"""SELECT EWD.*,EL.event_type,EL.event_method,EL.event_name,EL.event_title FROM {DB_PREFIX}.tbl_email_templates as EWD left join {DB_PREFIX}.event_list as EL ON EWD.event_id=EL.id 
    WHERE template_type='EMAIL' and EL.status = 'Y' {carrierWhere} {templateNameWhere} {stateWhere} {planTypeWhere}"""
    if 'datefrom' in request.form and request.form['datefrom']:
        datefrom = request.form['datefrom']
        datefrom = f"{datefrom} 00:00:00"
        Sql += f" AND EWD.create_date >= '{datefrom}' "
        count_query += f" AND EWD.create_date >= '{datefrom}' "

    if 'dateto' in request.form and request.form['dateto']:
        dateto = request.form['dateto']
        dateto = f"{dateto} 23:59:59"
        Sql += f" AND EWD.create_date <= '{dateto}' "
        count_query += f" AND EWD.create_date <= '{dateto}' "
        
    search_status=''
    if 'search_status' in request.form and request.form['search_status']:
        search_status = request.form['search_status']
        Sql += f" AND EWD.status = '{search_status}' "
        count_query += f" AND EWD.status = '{search_status}' "
    
    Sql		+=	f" limit {start},{disp_rec}"
        
    cursor.execute(count_query)
    total_count = cursor.fetchone()['total_count']
    total_recs	=	num = disp = total_count
    #include_once("notification_function.php")
    
    cursor.execute(Sql)
    result = cursor.fetchall()

    getevent_query = f"""SELECT id, event_name FROM {DB_PREFIX}.event_list 
                    WHERE status='Y' AND (event_method='Email and SMS' OR event_method='Email')"""
    cursor.execute(getevent_query)
    event_list = cursor.fetchall()
    
    carrier_list_query = f"select id,carrier_abbr from {DB_PREFIX}.tbl_carrier_master where status='Y'"
    cursor.execute(carrier_list_query)
    carrier_list = cursor.fetchall()
    company_qr = f"select state_name,state_abbrev as state_id from {DB_PREFIX}.tbl_states order by state_name asc"
    cursor.execute(company_qr)
    state_list = cursor.fetchall()
    getevent_preview = f"""SELECT EL.event_name,EWD.event_id, carrier_code, plan_type, reminders_days, EWD.id as rule_id FROM {DB_PREFIX}.tbl_email_templates as EWD left join {DB_PREFIX}.event_list as EL ON EWD.event_id=EL.id 
		WHERE 1 and EWD.status = 'Y' and template_type ='EMAIL'  ORDER BY  EWD.id DESC"""
    cursor.execute(getevent_preview)
    preview_events = cursor.fetchall()
    processed_preview_events = []

    for row in preview_events:
        carrier_code = ' || ' + row['carrier_code'].strip() if  row['carrier_code'] and  row['carrier_code'].strip() else ''
        plan_type = ' || ' + row['plan_type'].strip() if row['plan_type'] and row['plan_type'].strip() else ''

        daysRhs = json.loads(row['reminders_days']) if row['reminders_days'] else None
        days = ' || ' + daysRhs.get('1', '') + ' Day(s)' if isinstance(daysRhs, dict) else ''
        event_name = row['event_name'] if row['event_name'] else ''
        processed_preview_events.append({
            'id': row['event_id'],
            'event_name': row['event_name'],
            'rule_id': row['rule_id'],
            'selected': row['event_id'] == selected_template,
            'options': f'{event_name}{days}{carrier_code}{plan_type}'
        })
    sql_customer = f"SELECT id FROM {DB_PREFIX}.tbl_customer WHERE account_status = 'Active' ORDER BY id DESC LIMIT 1"
    cursor.execute(sql_customer)
    sql_customer_count = cursor.rowcount
    CustomerID = ''
    if sql_customer_count > 0:
        result_customer = cursor.fetchone()
        CustomerID = result_customer['id']
    return render_template('notification/view_notification.html', SHOW_OPTION_PLAN_TYPE=SHOW_OPTION_PLAN_TYPE,page=page, start=start, disp_rec=disp_rec,event_list=event_list,carrier_list=carrier_list,state_list=state_list,planTypeList=SHOW_OPTION_PLAN_TYPE,total_recs=total_recs,result=result,template_plan_type=template_plan_type,selected_template=selected_template,selected_states=selected_states,selected_carrier=selected_carrier,search_status=search_status,preview_events=processed_preview_events,CustomerID=CustomerID)

@app.route('/csr/ajax', methods=['POST'])
def common_ajax():
    action = request.form.get('action','')

    action_func = globals().get(action)
    if callable(action_func):
        data = action_func(request.form)
    else:
        data = {'error': 'Action function not found'}
    return jsonify(data)

def notificationPreview(form_data):
    cursor = get_db().cursor()
    carrier= carrier if 'carrier' in locals() else ''
    tab = form_data.get('tab','').strip()
    CustomerIDPosted = form_data.get('customer_id','').strip()
    notif_type = form_data.get('notif_type','').strip()
    event_id = form_data.get('eventID','').strip()
    update_id = form_data.get('rule_id','').strip()
    CustomerID=3087481
    if CustomerIDPosted:
        CustomerID = CustomerIDPosted
    catAndEvent = getEvnt(event_id)
    event_title  = catAndEvent['data']['event_title']
    is_carrier	  = catAndEvent['data']['is_carrier']
    event_method = catAndEvent['data']['event_method']
    event_name	  = catAndEvent['data']['event_name']
    query_company  = f"SELECT company_id, company_name from {DB_PREFIX}.tbl_service_company WHERE 1"
    cursor.execute(query_company)
    result_company = cursor.fetchone()
    company_id = result_company['company_id']
    company_name = result_company['company_name']
    event_method = 'BOTH' if event_method == 'Email and SMS' else event_method.upper()
    notifyType = notif_type
    Sql = f"SELECT email_body FROM {DB_PREFIX}.tbl_email_templates WHERE id='{update_id}' AND template_type='{notifyType}'"
    cursor.execute(Sql)
    result_sql = cursor.fetchone()
    email_body = result_sql['email_body']
    html = ''
    html += '<div class="row form-group">'
    html += '    <div class="col-lg-12 col-md-12 col-sm-12">'
    html += '        <div class="row">'
    html += '            <div class="col-lg-6 col-md-6 col-sm-6 col-xs-6"><label>Notification Type </label></div> <div class="col-lg-6 col-md-6 col-sm-6 col-xs-6"><span class="pull-right">Customer ID: ' + str(CustomerID) + '</span> </div></div>'
    html += '            <select name="evntList" id="evntList" class=" form-control" disabled="disabled"><option value="">' + str(event_name) + '</option></select>'
    html += '        </div>'
    html += '    </div>'
    html += '</div>'
    
    DrCrSql= f"select invoiceNumber from {DB_BILLING_PREFIX}.tbl_invoice_dr_cr_transaction where drcr_type='CR' order by id desc limit 1"
    cursor.execute(DrCrSql)
    rowcountDrCrSql = cursor.rowcount
    invoiceNumber = ""
    if rowcountDrCrSql > 0:
        DrCrData	= cursor.fetchone()
        invoiceNumber = DrCrData['invoiceNumber']
        
    templateVariables = {}
    templateVariables["%INVOICE_NUMBER%"] = invoiceNumber
    templateVariables["%ORDER_ID%"] = invoiceNumber
    GenericInsertNotification = GenericNotificationPreview(company_id ,CustomerID, event_title, carrier, templateVariables, notifyType, email_body)
    message = 'success'
    if GenericInsertNotification == '0':
        GenericInsertNotification = '<span class="col-lg-12" style="color:red"> Customer not found. </span>'
        message = 'fail'
    if notif_type == 'SMS' and message == 'success':
        html += '<div class="msgWrapper"><span class="msg_time">' + datetime.now().strftime("%H:%M") + '</span>'
        html += '    <div class="msginner">'
        html += '        <div class="user_info">'
        html += '            <div class="user_icon_msg">' + company_name[0] + '</div>'
        html += '            <div class="user_name_msg">' + company_name + '</div>'
        html += '        </div>'
        html += '        <div class="textMsg">text message</div>'
        html += '        <div class="MsgContent">'
        html += '            ' + nl2br(GenericInsertNotification)
        html += '        </div>'
        html += '    </div>'
        html += '</div>'
    else:
        html += '<div class="row form-group ">' + GenericInsertNotification + '</div>'
    response_array = {}
    response_array['result'] = html
    response_array['message']= message

    return response_array

def GenericNotificationPreview(CompanyID ,CustomerID, event_title, carrier, templateVariables={}, notifyType='', email_body=''):
    cursor = get_db().cursor()
    customerEmail= customerEmail if 'customerEmail' in locals() else ''
    sel_sql = f"SELECT EL.id,EL.event_type,EL.event_method,EL.event_name,EL.event_title,EL.is_carrier from {DB_PREFIX}.event_list as EL WHERE  status='Y' AND EL.event_title={quote_string(event_title)} ORDER BY  id DESC"
    cursor.execute(sel_sql)
    cntRecord = cursor.rowcount
    cur_date = datetime.now().strftime("%Y-%m-%d")
    insert_id=0
    if cntRecord > 0:
        enrollment_id = reviewers_notes = rejection_reason = lastfour_ccno = custom_template = added_by = plan_name = autopay_processed_amount = customer_password = tracking_no = mdn = nlad_anniversary_date = customer_plan_id = BILLING_ADDRESS = ''
        if CustomerID != 0:
            sqlmdn= f"select id,f_name,l_name, telephone_number,plan_id,email,account_status,ACCOUNT_NO, company_id,enroll_id,acco_pass, serv_add1,state,city,zip,serv_add2,mail_add1,mail_add2,billingcity,state_billing,billingzip,language,enrollment_type,carrier_id,accountType from {DB_PREFIX}.tbl_customer where  id='{CustomerID}'"
            cursor.execute(sqlmdn)
            rowmdn = cursor.fetchone()
            customer_name = rowmdn['f_name']
            to_name = f"{rowmdn['f_name']} {rowmdn['l_name']}"
            to_email = email_address = rowmdn['email']
            customer_phone_no = rowmdn['telephone_number']
            CompanyID = rowmdn['company_id']
            last_name = rowmdn['l_name']
            account_no = rowmdn['ACCOUNT_NO'] if rowmdn['ACCOUNT_NO'] != '' else rowmdn['id']
            enrollment_id = rowmdn['enroll_id']
            customer_password = rowmdn['acco_pass']
            customer_plan_id = rowmdn['plan_id']
            customer_state = rowmdn['state']
            customer_id = rowmdn['id']
            enrollment_type = rowmdn['enrollment_type']
            customer_language = rowmdn['language']
            completeAddress = f"{rowmdn['serv_add1']} {rowmdn['serv_add2']} {rowmdn['city']}, {rowmdn['state']} {rowmdn['zip']}"
            
            if templateVariables.get('%ORDER_ID%') or templateVariables.get('%INVOICE_NUMBER%'):
                PAYMENT_DATE = STORE_PURCHASE = ORDER_ID  = SHIPPING_ADDRESS = ACCESSORY = SUBTOTAL = TAXES = SHIPPING_CHARGE = LAST_FOUR_CC_NO = CREDIT_CARD_CHARGED_AMOUNT = INVOICE_AMOUNT = PAYMENT_METHOD =''
                if templateVariables.get('%INVOICE_NUMBER%'):
                    if '%INVOICE_NUMBER%' in templateVariables and templateVariables['%INVOICE_NUMBER%']:
                        invoiceNumber = templateVariables['%INVOICE_NUMBER%']

                    if '%ORDER_ID%' in templateVariables and templateVariables['%ORDER_ID%']:
                        invoiceNumber = templateVariables['%ORDER_ID%']
                        
                    DrCrSql= f"select * from {DB_BILLING_PREFIX}.tbl_invoice_dr_cr_transaction where drcr_type='DR' AND invoiceNumber='{invoiceNumber}'"
                    cursor.execute(DrCrSql)
                    DrCrData = cursor.fetchone()
                    DrCrCount = cursor.rowcount
                    if DrCrCount > 0:
                        PAYMENT_DATE = DrCrData['created_datetime']
                        INVOICE_AMOUNT = DrCrData['invoiceAmount']
                        PAYMENT_METHOD = DrCrData['paymentType']
                        duedate_dt = datetime.strptime(str(DrCrData['duedate']), '%Y-%m-%d %H:%M:%S')
                        INVOICE_DUE_DATE = duedate_dt.strftime('%m-%d-%Y')
                        STORE_PURCHASE = 'NA'
                        ACCESSORY ='NA'
                        SUBTOTAL = DrCrData['withouttaxamount']
                        TAXES = DrCrData['taxamount']
                        SHIPPING_CHARGE = 'NA'
                        sqlCardDels	=	f"SELECT * FROM tbl_card_detail WHERE requestID = '{DrCrData['reference_no']}'"
                        cursor.execute(sqlCardDels)
                        cntCardDels = cursor.rowcount
                        if cntCardDels > 0:
                            rowCardDels = cursor.fetchone()
                            cardNumber = rowCardDels['card_number']
                        
                
            return str(DrCrData['reference_no'])
            

    return str(cur_date)
    

def quote_string(input_str):
    return f"'{input_str}'"
    
    
def nl2br(s):
    return '<br />\n'.join(s.split('\n'))

def getEvnt(event_id):

    cursor = get_db().cursor()
    sql = f"""select id,event_name,event_type,event_method,status,category_id,	
            sent_immediate,default_template,default_sms, event_title,is_carrier from {DB_PREFIX}.event_list  where id=%s  limit 1"""
    cursor.execute(sql, (event_id,))
    results = cursor.fetchone()

    result_data = {}
    if results:
        result_data['statusCode'] = '00'
        result_data['data'] = {
            'id': results['id'],
            'event_name': results['event_name'],
            'event_type': results['event_type'],
            'event_method': results['event_method'],
            'category_id': results['category_id'],
            'sent_immediate': results['sent_immediate'],
            'default_template': results['default_template'],
            'default_sms': results['default_sms'],
            'event_title': results['event_title'],
            'is_carrier': results['is_carrier']
        }
    else:
        result_data['statusCode'] = '01'
        result_data['message'] = "There are no event names available."
    return result_data


    
    

if __name__ == '__main__':
    app.run(debug=True)