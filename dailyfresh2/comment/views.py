from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from goods.models import GoodsSKU
from comment.models import Comment
from utils.user_util import LoginRequiredMixin



class RecoverView(LoginRequiredMixin,View):
    def get(self,request,sku_id):
        user=request.user
        comment=request.GET.get('comment')
        print(comment)
        sku=GoodsSKU.objects.get(id=sku_id)
        comments=Comment.objects.create(user=user,sku=sku,content=comment)
        comments.save()
        data_list=[]
        comments=Comment.objects.filter(sku_id=sku_id)
        for comment in comments:
            d={}
            d['username']=user.username
            d['create_time']=comment.create_time
            d['comment']=comment.content
            data_list.append(d)
            ret={
                'ret':data_list
            }
            print(ret)
        return JsonResponse(ret)

class CheckView(LoginRequiredMixin,View):
    def get(self,request,sku_id):
        user = request.user
        comments = Comment.objects.filter(sku_id=sku_id)
        data_list = []
        for comment in comments:
            d={}
            d['username']=user.username
            d['create_time']=comment.create_time
            d['comment']=comment.content
            data_list.append(d)
            ret={
                'ret':data_list
            }
            print(ret)
        return JsonResponse(ret)



