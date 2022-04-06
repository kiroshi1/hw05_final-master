from http import HTTPStatus

from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post, User


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.author = User.objects.create_user(username='Author')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание группы'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст поста',
            group=cls.group, author=cls.author
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_author_client = Client()
        self.authorized_author_client.force_login(self.author)

    def test_urls_as_a_guest(self):
        """Неавторизованный пользователь получает
        доступ к доступным страницам.
        """
        url_list = ['/', f'/group/{self.group.slug}/']
        for adress in url_list:
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_new_redirect_as_a_guest(self):
        """Неавторизованный пользователь при создании поста
        перенаправляется на страницу авторизации.
        """
        response = self.guest_client.get('/new/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/new/')

    def test_edit_redirect_for_authorized_cleint(self):
        """Авторизованный пользователь(не автор) при попытке
        редактирования поста перенаправляется на страницу авторизации.
        """
        response = self.authorized_client.get(
            f'/{self.author}/{self.post.id}/edit/', follow=True)
        self.assertRedirects(response, f'/{self.author}/{self.post.id}/')

    def test_edit_redirect_for_guest_cleint(self):
        """Неавторизованный пользователь при создании поста
        перенаправляется на страницу авторизации.
        """
        response = self.guest_client.get(
            f'/{self.author}/{self.post.id}/edit/', follow=True)
        self.assertRedirects(
            response, f'/auth/login/?next=/{self.author}/{self.post.id}/edit/')

    def test_post_edit_as_a_guest(self):
        """Страница edit/ перенаправляет анонимного пользователя.
        """
        response = self.guest_client.get(
            f'/{self.author}/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_post_edit_as_a_authorized_client(self):
        """Страница edit/ перенаправляет авторизованного пользователя(не автора поста).
        """
        response = self.authorized_client.get(
            f'/{self.author}/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_urls_as_a_user(self):
        """Авторизованный пользователь получает доступ ко всем страницам."""
        url_list = [
            '/', f'/group/{self.group.slug}/', '/new/', f'/{self.author}/',
            f'/{self.author}/{self.post.id}/',
            f'/{self.author}/{self.post.id}/edit/',
        ]
        for adress in url_list:
            with self.subTest(adress=adress):
                response = self.authorized_author_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_404_error(self):
        """Проверка доступности адреса /page/about/."""
        response = self.guest_client.get('/thepage32512/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        urls = ['/new/', f'/{self.author}/{self.post.id}/edit/']
        for url in urls:
            templates_url_names = {
                'index.html': '/',
                'group.html': f'/group/{self.group.slug}/',
                'new.html': url,
            }
        for template, adress in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_author_client.get(adress)
                self.assertTemplateUsed(response, template)
