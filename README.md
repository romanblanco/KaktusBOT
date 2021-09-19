Telegram bot notifying about news from mobile operator [Kaktus](https://www.mujkaktus.cz)

![kaktusbot](https://cloud.githubusercontent.com/assets/1187051/24249960/7cb47ce8-0fd5-11e7-9020-91737720ab50.png)

```sh
echo "TELEGRAM:TOKEN" > ./TOKEN
docker build -t kaktusbotimg .
docker run -d -v $(pwd)/data:/data --name kaktusbot kaktusbotimg
```

[Give it a try!](https://telegram.me/KaktusBot)
