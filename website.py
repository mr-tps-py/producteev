from flask import Flask, render_template,redirect, url_for, request, session, send_from_directory
from passlib.hash import sha256_crypt
from MySQLdb import escape_string as thwart
from dbconnect import connection
from functools import wraps
from werkzeug import secure_filename
import gc, os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_secrets..!!!'
app.config['UPLOAD_FOLDER']='/home/lazarus/Desktop/FP/uploads/'

ALLOWED_EXTENSIONS=['zip']

def get_dev():
    cursor,conn=connection()
    cursor.execute("select username from users where user_type='developer'")
    data=cursor.fetchall()
    cursor.close()
    conn.close()
    return data

@app.route('/')
@app.route('/index.html')
def index():
    return render_template('index.html')

@app.route('/robots.txt')
def robots():
    robot_txt="User-agent: *<br>Disallow: /<br>Disallow: /register/<br>Disallow: /login/"
    return robot_txt


def login_required(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if 'logged_in' in session:
            return f(*args,**kwargs)
        else:
            return render_template("login.html",error="")
    return wrap


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/download/<string:task_name>',methods=['GET'])
@login_required
def download_zip(task_name):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'],filename=task_name+".zip")
    except Exception as e:
        return str(e)


@app.route('/upload/<string:task_name>',methods=['GET','POST'])
@login_required
def upload_zip(task_name):
    try:
        if request.method=='POST':
            file=request.files['file']
            if file and allowed_file(file.filename):
                filename=secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], task_name+".zip"))
                return '''Upload Successful<a href="javascript:window.history.back();" target="_blank" title="back">go back</a>'''
            else:
                return """Upload failed!!! Only zip files are allowed.<a href="javascript:window.history.back();" target="_blank" title="back">go back</a>"""
    except Exception as e:
        return str(e)

@app.route('/project/<int:project_id>',methods=['GET','POST'])
@login_required
def project(project_id):
    try:
        if request.method=='GET':
            cursor,conn=connection()
            cursor.execute("select * from projects where project_id={0}".format(project_id))
            data_p=cursor.fetchall()
            print(data_p)
            cursor.execute("select * from tasks where project_id='{0}'".format(project_id))
            data_t=cursor.fetchall()
            print(data_t)
            cursor.execute("select * from projects where manager='{0}'".format(thwart(session['username'])))
            data=cursor.fetchall()
            print(data)
            task={}
            for i in data_t:
                task[i[1]]=[i[3]]
            print(task)
            for i in task:
                print(i)
                cursor.execute("select devs from tasks where task_name='{0}'".format(i))
                data_t=cursor.fetchall()
                dev_list=[]
                for k in data_t:
                    dev_list.append(k[0])
                task[i].append(dev_list)
            cursor.close()
            conn.close()
            return render_template("project.html",data_p=data_p[0],datad=get_dev(),task=task,data=data)
        else:
            cursor,conn=connection()
            project_name=request.form['project_name']
            start_date=request.form['start_date']
            submission_date=request.form['submission_date']
            desc=request.form['desc']
            if(bool(project_name.strip())):
                cursor.execute("UPDATE `projects` SET `project_name` = '{0}' WHERE `projects`.`project_id` = '{1}'".format(project_name,project_id))
            if(bool(start_date.strip())):
                cursor.execute("UPDATE `projects` SET `start_date` = '{0}' WHERE `projects`.`project_id` = '{1}'".format(start_date,project_id))
            if(bool(submission_date.strip())):
                cursor.execute("UPDATE `projects` SET `deadline` = '{0}' WHERE `projects`.`project_id` = '{1}'".format(submission_date,project_id))
            if(bool(desc.strip())):
                cursor.execute("UPDATE `projects` SET `description` = '{0}' WHERE `projects`.`project_id` = '{1}'".format(desc,project_id))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('workspace'))
    except Exception as e:
        return str(e)


@app.route('/logout/')
@login_required
def logout():
    session.clear()
    gc.collect()
    return redirect(url_for("login"))

@app.route('/workspace/')
def workspace():
    cursor,conn=connection()
    data=False
    if session['user_type']=="manager" or session['user_type']=="admin":
        print("manager")
        if (session['user_type']=="manager"):
            cursor.execute("select * from projects where manager='{0}'".format(thwart(session['username'])))
        else:
            cursor.execute("select * from projects")
        data=cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template("workspace.html",data=data,datad=get_dev())
    elif(session['user_type']=="hr"):
        print("hr")
        print(session['logged_in'])
        cursor.execute("select * from projects")
        data=cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template("workspace.html",data=data,datad=get_dev())
    elif(session['user_type']=="client"):
        print("client")
        cursor.execute("select * from projects")
        data=cursor.fetchall()
        print(data)
        cursor.close()
        conn.close()
        return render_template("workspace.html",data=data,datad=get_dev())
    elif(session['user_type']=="developer"):
        print("dev")
        cursor.execute("select * from tasks where devs='{0}'".format(thwart(session['username'])))
        data=cursor.fetchall()
        task_pr={}
        for i in data:
            cursor.execute("select project_name from projects where project_id='{0}'".format(i[2]))
            pr_name=cursor.fetchall()
            task_pr[i[1]]=pr_name[0][0]
        cursor.close()
        conn.close()
        return render_template("workspace.html",data=data,datad=get_dev(),task_pr=task_pr)
    

@app.route('/create/', methods=['GET','POST'])
@login_required
def create():
    try:
        if request.method=="POST" and session['user_type']=="manager":
            cursor,conn=connection()
            project_name=request.form['project_name']
            start_date=request.form['start_date']
            submission_date=request.form['submission_date']
            desc=request.form['desc']
            if(bool(project_name.strip()) and bool(start_date.strip()) and bool(submission_date.strip()) and bool(desc.strip())):
                cursor.execute("insert into projects (project_name,start_date,deadline,description,manager) values ('{0}','{1}','{2}','{3}','{4}')".format(thwart(project_name),thwart(start_date),thwart(submission_date),thwart(desc),thwart(session['username'])))
                conn.commit()
                cursor.close()
                conn.close()
                gc.collect()
                return redirect(url_for("workspace"))
            else:
                return redirect(url_for("workspace"))
        return redirect(url_for("workspace"))
    except Exception as e:
        return str(e)

@app.route('/create_task/',methods=['GET','POST'])
@login_required
def create_task():
    try:
        if request.method=='POST':
            cursor,conn=connection()
            task_name=request.form['task_name']
            project_name=request.form['project_name']
            cursor.execute("select project_id from projects where project_name='{0}'".format(thwart(project_name)))
            project_id=cursor.fetchall()
            print(project_id)
            task_desc=request.form['desc']
            assigned_devs=request.form.getlist('dev_list')
            for dev in assigned_devs:
                cursor.execute("insert into tasks (task_name,project_id,task_desc,devs) values ('{0}','{1}','{2}','{3}')".format(thwart(task_name),(project_id[0][0]),thwart(task_desc),thwart(dev)))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('workspace'))
    except Exception as e:
        return str(e)+' ok'


@app.route('/task/<string:task_name>',methods=['GET','POST'])
@login_required
def task(task_name):
    try:
        cursor,conn=connection()
        cursor.execute("select * from projects where manager='{0}'".format(thwart(session['username'])))
        data=cursor.fetchall()
        cursor.execute("select * from tasks where task_name='{0}'".format(thwart(task_name)))
        data_t=cursor.fetchall()
        print(data_t)
        cursor.execute("select project_name from projects where project_id='{0}'".format(data_t[0][2]))
        pr_name=cursor.fetchall()
        print(pr_name)
        cursor.close()
        conn.close()
        return render_template("task.html",task_name=task_name,data_t=data_t,data=data,datad=get_dev(),pr_name=pr_name[0][0])
    except Exception as e:
        return str(e)


@app.route('/bug/',methods=['GET','POST'])
@login_required
def bug():
    try:
        return render_template('bug.html')
    except Exception as e:
        return str(e)


@app.route('/profile/',methods=['GET','POST'])
@login_required
def profile():
    try:
        cursor,conn=connection()
        if request.method=="POST":
            fname=request.form['fname']
            lname=request.form['lname']
            email=request.form['email']
            tel=request.form['telephone']
            password=request.form['password']
            cpassword=request.form['confirm']
            epassword=sha256_crypt.encrypt((password))
            if(bool(password.strip()) and bool(cpassword.strip()) and password==cpassword):
                cursor.execute("UPDATE `users` SET `first_name` = '{0}',`last_name` = '{1}',`email_id` = '{2}',`mobile_no` = '{3}',`password` = '{4}' WHERE `username` = '{5}'".format(thwart(fname),thwart(lname),thwart(email),tel,epassword,thwart(session['username'])))
                conn.commit()
                del password,cpassword,epassword
            else:
                cursor.execute("UPDATE `users` SET `first_name` = '{0}',`last_name` = '{1}',`email_id` = '{2}',`mobile_no` = '{3}' WHERE `username` = '{4}'".format(thwart(fname),thwart(lname),thwart(email),tel,thwart(session['username'])))
                conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for("profile"))
        cursor.execute("select * from users where username='{0}'".format(thwart(session['username'])))
        data=cursor.fetchall()
        print(data)
        cursor.close()
        conn.close()
        return render_template('profile.html',data=data)
    except Exception as e:
        return str(e)


@app.route('/login/', methods=['GET','POST'])
def login():
    try:
        if 'logged_in' in session:
            return redirect(url_for('workspace'))
        if request.method=="POST":
            username=request.form['username']
            if(bool(username.strip())):
                cursor,conn=connection()
                data=cursor.execute("select * from users where username='{0}'".format(thwart(username)))
                if(int(data)==0):
                    return render_template("login.html",error='Invalid Credentials!!')
                data=cursor.fetchone()[3]
                cursor.execute("select * from users where username='{0}'".format(thwart(username)))
                if sha256_crypt.verify(request.form['password'],data):
                    session['logged_in']=True
                    session['username']=username
                    session['user_type']=cursor.fetchone()[4]
                    cursor.close()
                    conn.close()
                    return redirect(url_for("workspace"))
                else:
                    cursor.close()
                    conn.close()
                    return render_template("login.html",error="Invalid Credentials")
            else:
                return render_template("login.html",error="Username can't be empty")
        gc.collect()
        return render_template("login.html")
    except Exception as e:
        return str(e)

@app.route('/register/',methods=['GET','POST'])
def register():
    try:
        if 'logged_in' in session:
            return redirect(url_for('workspace'))
        if request.method=="POST":
            cursor,conn=connection()
            username=request.form['username']
            if(bool(username.strip())):
                x=cursor.execute("select * from users where username='{0}'".format(thwart(username)))
                if(x>0):
                    cursor.close()
                    conn.close()
                    return render_template("register.html",error="Username not available")
            else:
                return render_template("register.html",error="Username can't be empty")
            email=request.form['email']
            if(bool(email.strip())):
                x=cursor.execute("select * from users where email_id='{0}'".format(thwart(email)))
                if(x>0):
                    cursor.close()
                    conn.close()
                    return render_template("register.html",error="Emaild exists. Login Instead.")
            else:
                return render_template("register.html",error="Email-id can't be empty")
            user_type=request.form['user_type']
            if user_type not in ['admin','hr','client','manager','developer']:
                return render_template("register.html",error=user_type)
            fname=request.form['fname']
            lname=request.form['lname']
            ph_no=request.form['telephone']
            password=request.form['password']
            c_password=request.form['confirm']
            if(password==c_password):
                password=sha256_crypt.encrypt((password))
                cursor.execute("insert into users (username,email_id,password,user_type,first_name,last_name,mobile_no) values ('{0}','{1}','{2}','{3}','{4}','{5}','{6}')".format(thwart(username),thwart(email),thwart(password),thwart(user_type),thwart(fname),thwart(lname),thwart(ph_no)))
                conn.commit()
                cursor.close()
                conn.close()
                gc.collect()
                return redirect(url_for('login'))
            else:
                cursor.close()
                conn.close()
                return render_template("register.html",error="Password should match.")
        return render_template('register.html')
    except Exception as e:
        return str(e)

@app.errorhandler(404)
def page_n_found(e):
	return render_template("404.html")

@app.errorhandler(405)
def method_n_found(e):
	return redirect(url_for('index'))

@app.errorhandler(500)
def server_n_found(e):
	return redirect(url_for('index'))

if __name__=="__main__":
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(debug=True, host='0.0.0.0',port=9999)
    print(dir(app))