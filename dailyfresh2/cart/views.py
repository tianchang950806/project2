from django.shortcuts import render
from django.views.generic import View

class CartView(View):
    def get(self,request):
        context={'page_name':1}
        return render(request,'cart/cart.html',context)
