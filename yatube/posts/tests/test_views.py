import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Comment, Follow, Group, Post, User

small_gif = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
    b'\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00'
    b'\x01\x00\x00\x02\x02\x44\x01\x00\x3b')


class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='test-slug',
            description='Тестовое описание группы')
        cls.post = Post.objects.create(
            text='Это тестовый текст',
            author=cls.user, group=cls.group,
            image=SimpleUploadedFile(
                name='small.gif', content=small_gif, content_type='image/gif'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_use_correct_template(self):
        cache.clear()
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            'index.html': reverse('index'),
            'group.html': reverse(
                'group_posts', kwargs={'slug': self.group.slug}),
            'new.html': reverse('new_post'),
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_url_pages_show_correct_context(self):
        url_list = [
            '/', f'/group/{self.group.slug}/', f'/{self.user}/',

        ]
        for adress in url_list:
            with self.subTest(adress=adress):
                cache.clear()
                response = self.authorized_client.get(adress)
                first_object = response.context['page'][0]
                post_text_0 = first_object.text
                post_author_0 = first_object.author
                post_group_0 = first_object.group
                post_image_0 = first_object.image
                self.assertEqual(post_text_0, self.post.text)
                self.assertEqual(post_author_0, self.user)
                self.assertEqual(post_group_0, self.group)
                self.assertEqual(post_image_0, self.post.image)

    def test_group_posts_pages_show_correct_context(self):
        """Шаблон group сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('group_posts', kwargs={'slug': self.group.slug})
        )
        post_image = response.context['page'][0].image
        self.assertEqual(response.context['group'].title, self.group.title)
        self.assertEqual(response.context['group'].slug, self.group.slug)
        self.assertEqual(
            response.context['group'].description, self.group.description)
        self.assertEqual(post_image, self.post.image)

    def test_post_page_shows_correct_context(self):
        """Шаблон post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'post', kwargs={'username': self.user, 'post_id': self.post.id}))
        first_object = response.context['post']
        post_text = first_object.text
        post_author = first_object.author
        post_group = first_object.group
        post_image = first_object.image
        self.assertEqual(post_text, self.post.text)
        self.assertEqual(post_author, self.user)
        self.assertEqual(post_group, self.group)
        self.assertEqual(post_image, self.post.image)

    def test_newpost_page_shows_correct_context(self):
        """Шаблон new сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('new_post'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_editpost_page_shows_correct_context(self):
        """Шаблон edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'edit', kwargs={'username': self.user, 'post_id': self.post.id}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_cache(self):
        cache.clear()
        post = Post.objects.create(
            text='Тестируем кэширование', author=self.user)
        response = self.client.get(reverse('index'))
        post_text1 = response.context['page'][0].text
        self.assertEqual(post.text, post_text1)
        post.delete()
        post_text2 = response.context['page'][0].text
        self.assertEqual(post_text2, post_text1)
        cache.clear()
        response = self.client.get(reverse('index'))
        post_text3 = response.context['page'][0]
        self.assertNotEqual(post_text3, post_text1)

    def test_user_subscribe(self):
        user2 = User.objects.create_user(username='TestUser2')
        self.authorized_client.get(reverse(
            'profile_follow', kwargs={'username': user2}))
        followers_count = Follow.objects.filter(
            user=self.user, author=user2).count()
        self.assertEqual(followers_count, 1)

    def test_user_unsubscribe(self):
        user2 = User.objects.create_user(username='TestUser2')
        Follow.objects.create(user=self.user, author=user2)
        followers_count = Follow.objects.filter(
            user=self.user, author=user2).count()
        self.assertEqual(followers_count, 1)
        self.authorized_client.get(reverse(
            'profile_unfollow', kwargs={'username': user2}))
        followers_count = Follow.objects.filter(
            user=self.user, author=user2).count()
        self.assertEqual(followers_count, 0)

    def test_follow_post_exists_in_follow_index(self):
        user2 = User.objects.create_user(username='TestUser2')
        post = Post.objects.create(text='Проверка подписки', author=user2)
        Follow.objects.create(user=self.user, author=user2)
        response = self.authorized_client.get(reverse(
            'follow_index'))
        post_text1 = response.context['page'][0].text
        self.assertEqual(post.text, post_text1)

    def test_unfollow_post_does_not_exists_in_follow_index(self):
        user2 = User.objects.create_user(username='TestUser2')
        post = Post.objects.create(text='Проверка подписки', author=user2)
        test_client = Client()
        test_client.force_login(user2)
        Follow.objects.create(user=user2, author=self.user)
        response = test_client.get(reverse(
            'follow_index'))
        post_text1 = response.context['page'][0].text
        self.assertNotEqual(post.text, post_text1)

    def test_auth_user_can_comment(self):
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовое создание поста',
        }
        self.authorized_client.post(
            reverse('add_comment', args=(self.user, self.post.pk)),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text=form_data['text'],
            ).first())

    def test_guest_user_cant_comment(self):
        guest_client = Client()
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовое создание поста',
        }
        response = guest_client.post(
            reverse('add_comment', args=(self.user, self.post.pk)),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertRedirects(
            response,
            f'/auth/login/?next=/{self.user}/{self.post.id}/comment/')


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title='Тестовый заголовк',
            slug='test-slug',
            description='Тестовое описание группы',
        )
        for number in range(12):
            cls.post = Post.objects.create(
                text=f'Тестовый пост {number}',
                author=cls.user, group=cls.group)

    def test_paginator(self):
        """Проверяет работу паджинатора(главная страница, профиль и группа)."""
        url_list = [
            '/', f'/group/{self.group.slug}/', f'/{self.user}/',
        ]
        for first_page in url_list:
            with self.subTest(first_page=first_page):
                cache.clear()
                response = self.client.get(first_page)
                self.assertEqual(len(
                    response.context.get('page').object_list), 10)
                second_page = first_page + '?page=2'
                response = self.client.get(second_page)
                self.assertEqual(len(
                    response.context.get('page').object_list), 2)


class NewPostCreateTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='test-slug',
            description='Тестовое описание группы')
        cls.post = Post.objects.create(
            text='Это тестовый текст', author=cls.user, group=cls.group)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_appears_on_url_pages(self):
        url_list = [
            '/', f'/group/{self.group.slug}/'
        ]
        for adress in url_list:
            with self.subTest(adress=adress):
                cache.clear()
                response = self.authorized_client.get(adress)
                first_object = response.context['page'][0]
                post_text_0 = first_object.text
                post_author_0 = first_object.author
                post_group_0 = first_object.group
                self.assertEqual(post_text_0, self.post.text)
                self.assertEqual(post_author_0, self.user)
                self.assertEqual(post_group_0, self.group)
