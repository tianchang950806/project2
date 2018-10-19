from django.shortcuts import render

def index(request):
    context = {'title': '天天生鲜-首页', 'guest_cart': 1}
    return render(request,'goods/index.html',context)

def detail(request):
    context = {'title': '天天生鲜-详情页面', 'guest_cart': 1}
    return render(request,'goods/detail.html',context)

def list(request):
    context = {'title': '天天生鲜-列表页面', 'guest_cart': 1}
    return render(request,'goods/list.html',context)