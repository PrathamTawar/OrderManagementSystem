#Order Management System


##To create migration files execute these before running containers:
- Linux environment use:
```./scripts/dev.sh run --rm --no-deps web python manage.py makemigrations```
- Windows environment use:
```docker compose -f compose.dev.yaml run --rm --no-deps web python manage.py makemigrations```



##Docker will automatically run ```migrate``` while executing ```docker compose up```


##For development build:
- Linux environment use:
```./scripts/dev.sh up --build```
- Windows environment use:
```docker compose -f compose.dev.yaml up --build```

##For production build use:
```docker compose up --build```