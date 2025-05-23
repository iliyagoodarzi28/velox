from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from .models import Blog, Category, Comment, Rating
from django.db.models import Q
from django.views.generic import ListView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .forms import CommentForm, BlogFilterForm, RatingForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg



def latest_posts(request):
    posts = Blog.objects.all().order_by('-created_at')[:3]  # آخرین ۳ مقاله
    return posts


class BlogView(View):
    def get(self, request):
        form = BlogFilterForm(request.GET or None)
        blogs = Blog.objects.all()  # Default to all blogs

        if form.is_valid():
            filter_choice = form.cleaned_data['filter_by']
            filter_map = {
                'most_viewed': '-views',  # Order by views in descending order
                'latest': '-date',        # Order by date in descending order
                'oldest': 'date',         # Order by date in ascending order
                'lowest_rating': 'average_rating',  # Assuming you have a way to aggregate ratings
                'highest_rating': '-average_rating', # Assuming you have a way to aggregate ratings
            }

            # Annotate blogs with average rating if filtering by rating
            if filter_choice in ['lowest_rating', 'highest_rating']:
                blogs = blogs.annotate(average_rating=Avg('ratings__score'))

            # Order the blogs based on the selected filter
            blogs = blogs.order_by(filter_map.get(filter_choice, 'date'))

        # Handle search query
        search_query = request.GET.get('q')
        if search_query:
            blogs = blogs.filter(
                Q(name__icontains=search_query) |
                Q(slug__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        return render(request, 'blog/blog.html', {
            'blogs': blogs,
            'form': form
        })






class BlogDetailView(View):
    def get(self, request, slug):
        blog = get_object_or_404(Blog, slug=slug)
        blog.views += 1
        blog.save()
        comments = blog.comments.all()
        form = CommentForm()
        rating_form = RatingForm()

        # بررسی اینکه آیا کاربر وارد شده است
        user_rating = None
        if request.user.is_authenticated:
            user_rating = blog.ratings.filter(user=request.user).first()

        average_rating = blog.ratings.aggregate(Avg('score')).get('score__avg', 0) or 0

        return render(request, 'blog/blog_detail.html', {
            'blog': blog,
            'comments': comments,
            'form': form,
            'rating_form': rating_form,
            'average_rating': average_rating,
            'user_rating': user_rating,  # ارسال امتیاز کاربر به الگو
        })

    def post(self, request, slug):
        blog = get_object_or_404(Blog, slug=slug)

        if not request.user.is_authenticated:
            return render(request, 'accounts/login_prompt.html', {
                'message': "شما ثبت نام نکرده‌اید. آیا می‌خواهید ثبت‌نام کنید یا وارد شوید؟"
            })

        # بررسی امتیازدهی
        if 'rating' in request.POST:
            # بررسی اینکه آیا کاربر قبلاً امتیاز داده است
            if blog.ratings.filter(user=request.user).exists():
                return redirect('blog_detail', slug=blog.slug)  # اگر امتیاز داده، به صفحه جزئیات برگرد

            rating_form = RatingForm(request.POST)
            if rating_form.is_valid():
                rating = rating_form.save(commit=False)
                rating.blog = blog
                rating.user = request.user
                rating.save()
                return redirect('blog_detail', slug=blog.slug)

        # بررسی نظرات
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.blog = blog
            comment.user = request.user
            comment.save()
            return redirect('blog_detail', slug=blog.slug)

        comments = blog.comments.all()
        average_rating = blog.ratings.aggregate(Avg('score')).get('score__avg', 0) or 0

        return render(request, 'blog/blog_detail.html', {
            'blog': blog,
            'comments': comments,
            'form': form,
            'rating_form': rating_form,
            'average_rating': average_rating,
        })


from django.views.generic import ListView, DetailView
from .models import Category


class CategoryListView(ListView):
    model = Category
    template_name = "blog/category_list.html"  # نام قالب لیست دسته‌بندی
    context_object_name = "categories"         # نام متغیر در کانتکست (اختیاری)
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) | Q(slug__icontains=q)
            )
        return queryset
    
                        # تعداد آیتم‌ها در هر صفحه (اختیاری)
class CategoryDetailView(DetailView):
    model = Category
    template_name = "blog/category_detail.html"
    context_object_name = "category"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # اضافه کردن تمامی دسته‌بندی‌ها برای ناوبری
        context['categories'] = Category.objects.all()
        # دریافت پارامتر جستجو (q)
        q = self.request.GET.get('q')
        if q:
            context['blogs'] = self.object.blogs.filter(
                Q(name__icontains=q) | Q(description__icontains=q)
            )
        else:
            context['blogs'] = self.object.blogs.all()
        return context








class CommentUpdateView(LoginRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/edit_comment.html'
    login_url = 'login'  # URL صفحه ورود

    def get_queryset(self):
        return Comment.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy('blog_detail', kwargs={'slug': self.object.blog.slug})

class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    template_name = 'blog/delete_comment.html'
    login_url = 'login'  # URL صفحه ورود

    def get_queryset(self):
        return Comment.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy('blog_detail', kwargs={'slug': self.object.blog.slug})
    


    

    