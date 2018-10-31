from django.shortcuts import render,redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer,SignatureExpired,BadSignature
from utils.user_util import LoginRequiredMixin
from celery_tasks.tasks import task_send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login,logout
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from .models import *
from django.http import *
import re
import random
from django.core.serializers import serialize
from redis import *
from goods.models import GoodsSKU
from order.models import OrderInfo,OrderGoods
from django.core.paginator import Paginator


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
        #调用celery task
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

               next_url=request.GET.get('next')
               print(next_url)
               if next_url:
                   resp=redirect(next_url)
               else:
                   resp=redirect('/goods/index')
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
            return render(request, 'user/ve_user/reset.html',{'user':user})

        except SignatureExpired as e:
            return HttpResponse('激活链接已过期')
        except BadSignature as e:
            return HttpResponse('激活链接非法')

class ModifyView(View):
    def post(self,request):
        uid=request.POST.get('uid','')
        print(uid)
        pwd1 = request.POST.get('newpwd1', '')
        pwd2 = request.POST.get('newpwd2', '')
        if not 8<=len(pwd1)<=20 or 8<=len(pwd2)<=20:
            return render(request, 'user/ve_user/reset.html', {'msg':'密码长度错误'})
        if pwd1 != pwd2:
            return render(request, 'user/ve_user/reset.html', {'msg': '密码不一致！'})
        else:
            user = User.objects.get(id=uid)
            user.set_password(pwd2)
            user.save()
            return render(request, 'user/login.html')



class LogOutView(View):
    def logout_view(request):
        #删除session
        logout(request)
        return redirect('/user/login')



class UserInfoView(LoginRequiredMixin,View):
    def get(self,request):
        user=request.user
        #读取历史记录
        #连接redis
        conn=StrictRedis('192.168.12.191')
        #获取用户历史记录的id
        history=conn.lrange('history_%d'%user.id,0,-1)

        # goodskus=GoodsSKU.objects.filter(id__in=history)

        goodskus=[]
        for hid in history:
            good=GoodsSKU.objects.get(id=hid)
            goodskus.append(good)


        try:
            address=Address.objects.get(user=user,is_default=True)
        except Address.DoesNotExist:
            address = None
        context={'title': '天天生鲜订单页面', 'page_name': 1,'page':1,'address':address,'goodskus':goodskus}
        return render(request,'user/user_center_info.html',context)


class UserOrderView(LoginRequiredMixin,View):
    def get(self,request,page):
        #获取用户订单信息
        user=request.user
        orders=OrderInfo.objects.filter(user=user).order_by('-create_time')
        for order in orders:
            order_skus=OrderGoods.objects.filter(order_id=order.order_id)
            for order_sku in order_skus:
                #计算小计
                amount=order_sku.count*order_sku.price
                #动态给order_sku增加属性，保存订单商品的小计
                order_sku.amount=amount
            # 动态给order增加属性，保存订单商品的信息
            order.order_skus=order_skus

        # 对数据进行分页
        paginator = Paginator(orders, 1)
        try:
            page=int(page)
        except Exception as e:
            page=1

        if page>paginator.num_pages:
            page=1
        #获取第page的Page实例对象
        order_page = paginator.page(page)

        #todo:进行页码的控制，页面上最多显示５个页码
        #1.总页数小于５页，页面上显示所有页码
        #2.如果当前页是前３页，显示１-5页
        #3.如果当前页是后３页，显示后５页
        #4.其他情况，显示当页的前２页　当页的后２页
        num_pages=paginator.num_pages
        if num_pages<5:
            pages=range(1,num_pages+1)
        elif page<=3:
            pages=range(1,6)
        elif num_pages-page<=2:
            pages=range(num_pages-4,num_pages+1)
        else:
            pages=range(page-2,page+3)

        context = {'title':'天天生鲜订单页面',
                   'page_name':1,
                   'page':2,
                   'pages':pages,
                   'order_page':order_page,
                   }
        return render(request,'user/user_center_order.html',context)




class UserSiteView(LoginRequiredMixin,View):
    def get(self, request):
        user=request.user
        address_all=Address.objects.filter(user=user)
        print(address_all)
        try:
            address=Address.objects.get(user=user,is_default=True)
        except Address.DoesNotExist:
            address=None
        context = {'title': '天天生鲜用户中心', 'page_name': 1,'page':3,'address':address,'address_all':address_all}
        return render(request, 'user/user_center_site.html',context)

#地址处理类
class UserSiteHandleView(LoginRequiredMixin,View):
    def get(self,request):

        user = request.user
        aid = request.GET.get('aid')
        default_address = Address.objects.get(id=aid)

        try:
            address = Address.objects.get(user=user, is_default=True)
            address.is_default = False
            address.save()
        except Address.DoesNotExist:
            pass
        if default_address:
            default_address.is_default = True
            default_address.save()

        context = {'title': '天天生鲜用户中心', 'page_name': 1, 'page': 3}
        return render(request, 'user/user_center_site.html', context)

#添加地址类
class UserInsertView(LoginRequiredMixin,View):
    def get(self,request):
        user = request.user
        try:
          address=Address.objects.get(user=user, is_default=True)
        except Address.DoesNotExist:
            address = None
        context = {'title': '新增地址页面', 'page_name': 1, 'page': 3,'address':address}
        return render(request, 'user/insert_address.html', context)

    def post(self,request):
        user = request.user
        ureceiver = request.POST.get('receiver')
        uaddress = request.POST.get('address')
        print(type(uaddress))
        ucode = request.POST.get('code')
        uphone = request.POST.get('phone')
        pro_id=request.POST.get('pro_id')
        city_id=request.POST.get('city_id')
        dis_id=request.POST.get('dis_id')
        if pro_id!='' and city_id!='' and dis_id!='':
            pro=AreaInfo.objects.filter(id=pro_id)[0]
            city=AreaInfo.objects.filter(id=city_id)[0]
            dis=AreaInfo.objects.filter(id=dis_id)[0]

            uaddress=str(pro)+str(city)+str(dis)+uaddress
            print(uaddress)
            if not all([ureceiver, uaddress, ucode, uphone]):
                context = {'title': '新增地址页面', 'page_name': 1, 'page': 3, 'error_msg': '数据不完整'}
                return render(request, 'user/insert_address.html', context)
            if not re.match(r'1[3|4|5|7|8][0-9]{9}$', uphone):
                context = {'title': '新增地址页面', 'page_name': 1, 'page': 3, 'error_msg': '手机号不正确'}
                return render(request, 'user/insert_address.html', context)
            try:
                address = Address.objects.filter(user=user,receiver=ureceiver,addr=uaddress, zip_code=ucode, phone=uphone,)
            except Address.DoesNotExist:
                address = None
            if address:
                context={'title': '新增地址页面', 'page_name': 1, 'page': 3,'error_msg': '地址已存在'}
                return render(request, 'user/insert_address.html', context)
            try:
                address = Address.objects.get(user=user, is_default=True)
                address.is_default = False
                address.save()
            except Address.DoesNotExist:
                pass
            Address.objects.create(user=user, receiver=ureceiver, addr=uaddress, zip_code=ucode, phone=uphone,
                                             is_default=True)

            return redirect('/user/site')
        else:
            context = {'title': '新增地址页面', 'page_name': 1, 'page': 3,'error_msg': '地址填写不完整，请重新输入'}
            return render(request, 'user/insert_address.html', context)

#编辑地址类
class UserEditView(LoginRequiredMixin,View):
    def get(self,request):
        id=request.GET.get('id')
        order = request.GET.get('order', '')

        address = Address.objects.get(id=id)
        context = {'title': '编辑地址页面', 'page_name': 1, 'page': 3,'address':address,'order':order}
        return render(request, 'user/edit_address.html', context)
    def post(self,request):
        aid = request.POST.get('aid')
        ureceiver = request.POST.get('receiver')
        uaddress = request.POST.get('address')
        ucode = request.POST.get('code')
        uphone = request.POST.get('phone')
        pro_id = request.POST.get('pro_id','')
        city_id = request.POST.get('city_id','')
        dis_id = request.POST.get('dis_id','')
        order=request.POST.get('order','')
        try:
            pro = AreaInfo.objects.filter(id=pro_id)[0]
            city = AreaInfo.objects.filter(id=city_id)[0]
            dis = AreaInfo.objects.filter(id=dis_id)[0]
        except:
            context = {'title': '编辑地址页面', 'page_name': 1, 'page': 3, 'error_msg': '地址填写不完整，请重新输入'}
            return render(request, 'user/edit_address.html', context)
        else:
            uaddress = str(pro) + str(city) + str(dis) + uaddress

        #查询
        address = Address.objects.get(id=aid)
        #修改
        address.receiver=ureceiver
        address.addr=uaddress
        address.zip_code=ucode
        address.phone=uphone
        address.save()
        if order:
            return redirect('/order/place')
        else:
            return redirect('/user/site')

#删除地址类
class UserDeleteView(LoginRequiredMixin,View):
    def get(self,request,aid):
        address=Address.objects.get(id=aid)
        address.delete()
        return redirect('/user/site')


def pro(request):
    prolist=AreaInfo.objects.filter(parea__isnull=True)
    area=serialize('json',prolist,fields=['id','title'])
    return JsonResponse({'area':area})

def city(request,id):
    citylist=AreaInfo.objects.filter(parea_id=id)
    list=[]
    for i in citylist:
        d={}
        d['id']=i.id
        d['title']=i.title
        list.append(d)
    return JsonResponse({'area': list})










