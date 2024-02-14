from flask import Flask, render_template,session, redirect, url_for,request,json
from db import get_db, close_db

app = Flask(__name__)
PROJECT_SESSION_USER = 'user'

# @app.before_request
# def check_session():
#     if hasattr(g, 'ajaxcall') and g.ajaxcall:
#         # Assume g.ajaxcall is a global variable for AJAX calls
#         if PROJECT_SESSION_USER not in session or not session[PROJECT_SESSION_USER]:
#             g.ajaxcall = False
#             return {'error': 'Your Telgoo5 session has timed out. Please sign in again to continue.'}, 401

#     elif PROJECT_SESSION_USER not in session or not session[PROJECT_SESSION_USER]:
#         return redirect(url_for('index'))
    
@app.route('/view-email-notification', methods=['GET','POST'])
def view_email_notification():
    cursor = get_db().cursor()
    print(request.form)
    page = request.args.get('page', default=0, type=int)
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
    
    count_query = f"""SELECT COUNT(*) as total_count FROM tbl_email_templates as EWD 
                    LEFT JOIN event_list as EL ON EWD.event_id = EL.id 
                    WHERE template_type='EMAIL' and EL.status = 'Y' {carrierWhere} {templateNameWhere} {stateWhere} {planTypeWhere}"""


    Sql = f"""SELECT EWD.*,EL.event_type,EL.event_method,EL.event_name,EL.event_title FROM tbl_email_templates as EWD left join event_list as EL ON EWD.event_id=EL.id 
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

    getevent_query = """SELECT id, event_name FROM event_list 
                    WHERE status='Y' AND (event_method='Email and SMS' OR event_method='Email')"""
    cursor.execute(getevent_query)
    event_list = cursor.fetchall()
    
    carrier_list_query = "select id,carrier_abbr from tbl_carrier_master where status='Y'"
    cursor.execute(carrier_list_query)
    carrier_list = cursor.fetchall()
    company_qr = "select state_name,state_abbrev as state_id from tbl_states order by state_name asc"
    cursor.execute(company_qr)
    state_list = cursor.fetchall()
    getevent_preview = f"""SELECT EL.event_name,EWD.event_id, carrier_code, plan_type, reminders_days, EWD.id as rule_id FROM tbl_email_templates as EWD left join event_list as EL ON EWD.event_id=EL.id 
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
            'selected': row['event_id'] == selected_template,
            'options': f'{event_name}{days}{carrier_code}{plan_type}'
        })
    return render_template('notification/view_notification.html', SHOW_OPTION_PLAN_TYPE=SHOW_OPTION_PLAN_TYPE,page=page, start=start, disp_rec=disp_rec,event_list=event_list,carrier_list=carrier_list,state_list=state_list,planTypeList=SHOW_OPTION_PLAN_TYPE,total_recs=total_recs,result=result,template_plan_type=template_plan_type,selected_template=selected_template,selected_states=selected_states,selected_carrier=selected_carrier,search_status=search_status,preview_events=processed_preview_events)

if __name__ == '__main__':
    app.run(debug=True)