To create migration files use:
```docker compose -f compose.dev.yaml run --rm --no-deps web python manage.py makemigrations```
before running containers


Docker will automatically run ```migrate``` while executing ```docker compose up```


For development build use:
```docker compose -f compose.dev.yaml up --build```

For production build use:
```docker compose up --build```