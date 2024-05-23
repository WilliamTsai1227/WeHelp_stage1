from fastapi import FastAPI, Request, Form ,Query
from fastapi.responses import RedirectResponse,HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import mysql.connector
from pydantic import BaseModel
import re




app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(SessionMiddleware, secret_key="secret")

# verify input is empty or not
def verify_NotEmpty_input(name,account,password):
    if name is None or account is None or password is None:
        return False
    return True
#verify password format and length
def verify_password(password,min_length,max_length):
    lowercase = re.search(r'[a-z]',password)
    uppercase = re.search(r'[A-Z]',password)
    is_number = re.search(r'\d',password)
    is_special_letters = re.search(r'[@#$%]',password)
    if len(password)< min_length or len(password)>max_length:
        return False
    if lowercase is None or uppercase is None or is_number is None or is_special_letters is None:
        return False
    return True

@app.get("/")
async def home(request: Request):
    if "SIGNED-IN" not in request.session or request.session["SIGNED-IN"] != True : #如果尚未登入，顯示home page
        return templates.TemplateResponse("Home_page.html",{"request": request})
    elif request.session["SIGNED-IN"] == True : #如果已經登入了顯示會員頁
        return RedirectResponse(url="/member", status_code=303)
    
@app.post("/signup")
async def signup(request: Request,register_name: str= Form(None),register_account: str= Form(None), register_password: str= Form(None)):
    #verify input is empty or not
    #verify password length and format
    #All pass will enter the database procedure.
    if verify_NotEmpty_input(register_name,register_account,register_password) and verify_password(register_password,4,8):
        con = mysql.connector.connect(
            user = "root",
            password = "12345678",
            host = "localhost",
            database = "website"
        )
        name = register_name
        account = register_account
        password = register_password
        
        #創建cursor物件
        cursor = con.cursor()
        cursor.execute("SELECT username FROM member WHERE username=%s",(account,)) #尋找相同帳號
        data = cursor.fetchall()
        if data == []: #沒找到
            cursor.execute("INSERT INTO member(name,username,password) VALUES (%s,%s,%s)",(name,account,password))
            con.commit()
            con.close()
            return RedirectResponse(url="/", status_code=303)
        if data != []: #找到相同帳號
            con.close()
            error_message = "Repeated username"
            return RedirectResponse(url=f"/error?message={error_message}", status_code=303)
    else:
        error_message = "註冊失敗"
        return RedirectResponse(url=f"/error?message={error_message}", status_code=303)

    
    


@app.post("/signin")
async def signin(request: Request,account: str= Form(None), password: str= Form(None)):
    #verify input is empty or not
    #verify password length and format 
    #All pass will enter the database procedure.
    name = "default"
    if verify_NotEmpty_input(name,account,password) and verify_password(password,4,8):
        con = mysql.connector.connect(
            user = "root",
            password = "12345678",
            host = "localhost",
            database = "website"
        )
        cursor = con.cursor()
        cursor.execute("SELECT id, name, username, password FROM member WHERE username=%s AND password=%s",(account,password))
        data = cursor.fetchone()
        con.close()
        if data == None:
            error_message = "帳號或密碼輸入錯誤"
            request.session["SIGNED-IN"] = False
            return RedirectResponse(url=f"/error?message={error_message}", status_code=303)
        if account == data[2] and password == data[3]:     
            request.session.update({"SIGNED-IN": True, "id": data[0], "name": data[1], "username":data[2]})
            return RedirectResponse(url="/member", status_code=303)
    else:
        error_message = "驗證失敗"
        return RedirectResponse(url=f"/error?message={error_message}", status_code=303)



@app.get("/member")
async def member(request: Request):    
    if "SIGNED-IN" not in request.session or request.session["SIGNED-IN"] == False :
        return RedirectResponse(url="/")
    elif request.session["SIGNED-IN"] == True:
        id = request.session["id"] #登入會員id
        print(type(id))
        con = mysql.connector.connect( #連接資料庫
            user = "root",
            password = "12345678",
            host = "localhost",
            database = "website"
        )
        cursor = con.cursor()
        cursor.execute("SELECT name FROM member WHERE id=%s",(id,)) #現在這個會員的姓名
        name_list=cursor.fetchone()
        name = name_list[0]
        cursor.execute("SELECT member.name, message.content, message.member_id, message.id FROM member INNER JOIN message ON member.id = message.member_id ORDER BY message.time DESC;")
        data = cursor.fetchall()
        result = []
        for item in data:
            empty = [] #之後要單獨存放每一筆資料的小list
            check = "" 
            message_username = item[0]  #留言人名稱
            message = item[1] #留言內容
            member_id = item[2] #留言會員id
            message_id = item[3] #這則message id
            if id == member_id: #若登入id和留言會員id吻合，創造打叉按鈕
                check = '<button>X</button>'
            empty.append(message_username+":")
            empty.append(message)
            empty.append(check)
            empty.append(message_id)
            result.append(empty) # result=[[message_username,message,check,message_id]....]
        
        con.close()
        return templates.TemplateResponse("Success_page.html", {"result": result, "id": id, "name": name, "request": request}, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    
@app.get("/api/member")
async def query_member(request: Request, username: str = Query(..., description="要查詢的會員帳號"), ):
    if "SIGNED-IN" not in request.session or request.session["SIGNED-IN"] == False :
        return {"data": None}
    elif request.session["SIGNED-IN"] == True:
        con = mysql.connector.connect( 
                user = "root",
                password = "12345678",
                host = "localhost",
                database = "website"
            )
        cursor = con.cursor()
        cursor.execute("SELECT id, name, username FROM member WHERE username=%s",(username,))
        data = cursor.fetchone()
        con.close()
        if data:
            database_user_id = data[0]
            database_name = data[1]
            database_username = data[2]
            result = {
                "data": {
                    "id": database_user_id,
                    "name": database_name,
                    "username": database_username
                }
            }
            return result
        # 如果找不到匹配的会员
        return {"data": None}
    
    


@app.patch("/api/member")
async def update_member_name(request: Request):
    if "SIGNED-IN" not in request.session or request.session["SIGNED-IN"] == False :
        return {"error":True} 
    elif request.session["SIGNED-IN"] == True:
        update_data = await request.json()
        new_name = update_data.get("name").strip()
        if new_name == "":
            return {"error":True}
        if new_name != "":
            user_id = request.session["id"] 
            con = mysql.connector.connect( 
                    user = "root",
                    password = "12345678",
                    host = "localhost",
                    database = "website"
                )
            cursor = con.cursor()
            cursor.execute("UPDATE member SET name = %s WHERE id= %s",(new_name,user_id))
            con.commit()
            con.close()
            if cursor.rowcount > 0:
                # 更新成功
                return {"ok":True}
            else:
                # 更新失败
                return {"error":False}
    else:
        return {"error":True}       



@app.get("/error")
async def error(request: Request,message: str=None):
    return templates.TemplateResponse("Error_page.html",{"error_message": message,"request": request})

@app.get("/signout")
async def logout(request: Request):
    request.session.update({"SIGNED-IN": False, "id": None, "name": None, "username":None})
    return RedirectResponse(url="/")


@app.post("/createMessage")
async def createMessage(request: Request,message: str= Form("empty")):
    con = mysql.connector.connect(
        user = "root",
        password = "12345678",
        host = "localhost",
        database = "website"
    )
    cursor = con.cursor()
    id = request.session["id"]  #現在的使用者id
    cursor.execute("INSERT INTO message(member_id,content) VALUES (%s,%s)",(id,message)) #寫入message table 
    con.commit()
    con.close()
    return RedirectResponse(url="/member", status_code=303)

@app.post("/deleteMessage")
async def deleteMessage(request: Request):
    #從前端javascript拿到json格式資料
    message_data = await request.json()

    # 解析出messageID
    messageId = int(message_data.get("messageId")) #留言的使用者id 傳進來data type 為 str 要記得轉int
   
    con = mysql.connector.connect(
        user = "root",
        password = "12345678",
        host = "localhost",
        database = "website"
    )
    cursor = con.cursor()
    cursor.execute("SELECT member_id FROM message WHERE id=%s",(messageId,))
    result = cursor.fetchone()
    if result:
        member_id = result[0]
        if member_id == request.session["id"]: #如果這則留言的留言者id與現在的登入使用者id一樣了話允許刪除
            cursor.execute("DELETE FROM message WHERE id=%s",(messageId,))
            con.commit()
    con.close()
    return RedirectResponse(url="/member", status_code=303)

    

