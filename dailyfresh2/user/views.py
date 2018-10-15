from django.shortcuts import render,redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer,SignatureExpired,BadSignature
from utils.user_util import LoginRequiredMixin
from celery_tasks.tasks import task_send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from .models import *
from django.http import *
import re
import random




class RegisterView(View):
    '''视图类'''
    def get(self,request):
        '''注册页面'''
        context = {'title': '用户注册'}
        return render(request, 'user/register.html', context)
    def post(self,request):
        '''注册处理'''
        uname = request.POST.get('user_name').strip()
        upwd = request.POST.get('pwd').strip()
        ucpwd = request.POST.get('cpwd').strip()
        uemail = request.POST.get('email').strip()
        uallow = request.POST.get('allow', '').strip()


        if not all([uname, upwd, ucpwd, uemail]):
            context= {'title': '用户注册','error_msg': '数据不完整'}
            return render(request, 'user/register.html',context)

        try:
            user = User.objects.get(username=uname)
        except User.DoesNotExist:
            user = None
        if user:
            context={'title': '用户注册','error_name': '用户名已存在'}
            return render(request, 'user/register.html', context)

        if not 8<=len(upwd)<=20:
            context={'title': '用户注册','error_pwd':'密码长度错误'}
            return render(request, 'user/register.html', context)

        if (upwd != ucpwd):
            context={'title': '用户注册','error_cpwd':'密码不一致'}
            return render(request, 'user/register.html',context)

        if not re.match('^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', uemail):
            context={'title': '用户注册','error_mail': '邮箱格式不正确'}
            return render(request, 'user/register.html', context)

        if uallow != 'on':
            context={'title': '用户注册','error_allow': '请同意协议'}
            return render(request, 'user/register.html', context)


        # 创建对象
        user = User.objects.create_user(uname, uemail, upwd)
        user.is_active = 0
        user.save()

        #加密用户的身份信息，生成激活token
        serializer=Serializer(settings.SECRET_KEY,3600)
        info={'confirm':user.id}
        token=serializer.dumps(info).decode()
        encryption_url='http://192.168.12.191:8888/user/active/%s'%token

        #发邮件
        subject='天天生鲜'   #邮件的标题
        message=''    #文本内容
        sender=settings.EMAIL_FROM
        receiver=[uemail]
        html_message='<h1>%s,欢迎你成为天天生鲜注册会员</h1>请点击下面链接激活您的账户</br><a href="%s">%s</a>'%(uname,encryption_url,encryption_url)  #html内容

        #发送
        task_send_mail.delay(subject, message,sender,receiver,html_message)
        # 注册成功转向登录页面
        return redirect(reverse('user:login'))


class ActiveView(View):
    def get(self,request,token):
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info=serializer.loads(token)
            #获取激活码用户的id
            user_id=info['confirm']

            #根据id获取用户信息
            user=User.objects.get(id=user_id)
            user.is_active=1
            user.save()
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            return HttpResponse('激活链接已过期')
        except BadSignature as e:
            return HttpResponse('激活链接非法')


class LoginView(View):
    def get(self,request):
        '''登录页面'''
        remember_uname = request.COOKIES.get('remember_uname', '')
        context = {'title': '用户登录', 'remember_uname': remember_uname}
        return render(request, 'user/login.html', context)
    def post(self,request):
        username = request.POST['username']
        password = request.POST['pwd']
        remember=request.POST['remember']
        verifycode = request.POST['verifycode'].strip().lower()
        if not all([username,password]):
            context={'title': '用户登录','error_msg': '数据不完整'}
            return render(request, 'user/login.html',context)

        if verifycode != request.session["validate_code"].lower():
            return render(request, 'user/login.html', {'error_verifycode': '验证码错误'})

        user = authenticate(username=username,password=password)
        print(user)
        if user is not None:
            if user.is_active:
               #记录用户的登录状态
               login(request, user)
               # print(request.GET.get('next','get请求．．'))
               # print(request.POST.get('next', 'post请求．．'))
               next_url=request.GET.get('next')
               print(next_url)
               if next_url:
                   resp=redirect(next_url)
               else:
                   resp=render(request,'user/index.html')
               if remember == '1':
                   resp.set_cookie('remember_uname', username, 3600 * 24 * 7)
               else:
                   resp.set_cookie('remember_uname', username, 3600 * 0)
               return resp


            else:
                context={'title': '用户登录','error_msg':'用户未激活'}
                return render(request, 'user/login.html', context)
        else:
            context = {'title': '用户登录', 'error_msg': '用户名或密码错误'}
            return render(request, 'user/login.html', context)


def validate_code(request):
    # 定义变量，用于画面的背景色、宽、高
    bgcolor = (random.randrange(20, 100), random.randrange(20, 100), 255)
    width = 100
    height = 25
    # 创建画面对象
    im = Image.new('RGB', (width, height), bgcolor)
    # 创建画笔对象
    draw = ImageDraw.Draw(im)
    # 调用画笔的point()函数绘制噪点
    for i in range(0, 200):
        xy = (random.randrange(0, width), random.randrange(0, height))
        fill = (random.randrange(0, 255), random.randrange(0, 255), random.randrange(0, 255))
        draw.point(xy, fill=fill)
    # 定义验证码的备选值
    str1 = 'abcd123efgh456ijklmn789opqr0stuvwxyzABCD123EFGHIJK456LMNOPQRS789TUVWXYZ0'
    # 随机选取4个值作为验证码
    rand_str = ''
    for i in range(0, 4):
        rand_str += str1[random.randrange(0, len(str1))]


    #保存到sesison
    request.session["validate_code"] = rand_str

    # 构造字体对象
    font = ImageFont.truetype(settings.FONT_STYLE, 23)
    # 绘制4个字
    for i in range(4):
        # 构造字体颜色
        fontcolor = (255, random.randrange(0, 255), random.randrange(0, 255))
        draw.text((5+24*i, 2), rand_str[i], font=font, fill=fontcolor)

    # 释放画笔
    del draw

    buf = BytesIO()
    # 将图片保存在内存中，文件类型为png
    im.save(buf, 'png')
    # 将内存中的图片数据返回给客户端，MIME类型为图片png
    return HttpResponse(buf.getvalue(), 'image/png')


class ForgetPwdView(View):
    def get(self,request):
        return render(request, 'user/ve_user/forget.html')
    def post(self,request):
        name=request.POST.get('uname')
        email = request.POST.get('uemail')
        request.session["forget_user_name"]=name
        blog_user = User.objects.filter(username=name,email=email)
        if blog_user:
            serializer = Serializer(settings.SECRET_KEY, 3600)
            info = {'confirm': blog_user.values()[0]['id']}
            token = serializer.dumps(info).decode()
            encryption_url = 'http://192.168.12.191:8888/user/reset/%s' % token

            # 发邮件
            subject = '天天生鲜'  # 邮件的标题
            message = ''  # 文本内容
            sender = settings.EMAIL_FROM
            receiver = [email]
            html_message = '<h1>%s,欢迎你成为天天生鲜注册会员</h1>请点击下面链接激活重置您的密码</br><a href="%s">%s</a>' % (
            name, encryption_url, encryption_url)  # html内容

            # 发送
            task_send_mail.delay(subject, message, sender, receiver, html_message=html_message)
            return render(request, 'user/login.html')
        else:
            return render(request, 'user/ve_user/forget.html', {'msg': '该用户不存在，请确认该邮箱注册过账号'})

class ResetPwdView(View):
    def get(self,request,token):
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            # 获取激活码用户的id
            user_id = info['confirm']

            # 根据id获取用户信息
            user = User.objects.get(id=user_id)
            return render(request, 'user/ve_user/reset.html',{'email':user.email})

        except SignatureExpired as e:
            return HttpResponse('激活链接已过期')
        except BadSignature as e:
            return HttpResponse('激活链接非法')


class ModifyPwdView(View):
    def post(self,request):
        name = request.session.get("forget_user_name")
        print(name)
        pwd1 = request.POST.get('newpwd1', '')
        pwd2 = request.POST.get('newpwd2', '')
        if pwd1 != pwd2:
            return render(request, 'user/ve_user/reset.html', {'msg': '密码不一致！'})

        else:
            user = User.objects.get(username=name)
            user.set_password(pwd2)
            user.save()
            return render(request, 'user/login.html')




class UserInfoView(LoginRequiredMixin,View):
    def get(self,request):
        context={'page':'1'}
        return render(request,'user/user_center_info.html',context)


class UserOrderView(LoginRequiredMixin,View):
    def get(self,request):
        context = {'page': '2'}
        return render(request,'user/user_center_order.html',context)

class UserSiteView(LoginRequiredMixin,View):
    def get(self, request):
        context = {'page': '3'}
        return render(request, 'user/user_center_site.html',context)

