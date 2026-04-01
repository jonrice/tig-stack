
![Logo](https://user-images.githubusercontent.com/64506580/159311466-f720a877-6c76-403a-904d-134addbd6a86.png)


# Telegraf, InfluxDB, Grafana (TIG) Stack

Gain the ability to analyze and monitor telemetry data by deploying the TIG stack within minutes using [Docker](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/).




## ⚡️ Getting Started

Clone the project

```bash
  git clone https://github.com/huntabyte/tig-stack.git
```

Navigate to the project directory

```bash
  cd tig-stack
```

Change the environment variables define in `.env` that are used to setup and deploy the stack
```bash
├── telegraf/
├── .env         <---
├── docker-compose.yml
├── entrypoint.sh
└── ...
```

Customize the `telegraf.conf` file which will be mounted to the container as a persistent volume

```bash
├── telegraf/
│   ├── telegraf.conf <---
├── .env
├── docker-compose.yml
├── entrypoint.sh
└── ...
```

Start the services
```bash
docker-compose up -d
```
## Docker Images Used (Official & Verified)

[**Telegraf**](https://hub.docker.com/_/telegraf) / `1.19`

[**InfluxDB**](https://hub.docker.com/_/influxdb) / `2.1.1`

[**Grafana-OSS**](https://hub.docker.com/r/grafana/grafana-oss) / `8.4.3`


## 🔔 iOS Push Notifications

The stack includes a lightweight webhook service (`notifications/`) that
forwards Grafana alert payloads as **iOS push notifications** via the
Apple Push Notification service (APNs).

### How it works

1. Grafana fires an alert and calls `POST http://<host>:8080/webhook`.
2. The webhook service authenticates with APNs using a JWT bearer token
   derived from your `.p8` private key.
3. A push notification is delivered to every device token listed in
   `APNS_DEVICE_TOKENS`.

### Setup

#### 1 – Create an APNs key in the Apple Developer portal

1. Go to **Certificates, Identifiers & Profiles → Keys**.
2. Create a new key, enable **Apple Push Notifications service (APNs)**.
3. Download the `.p8` file and note the **Key ID** and your **Team ID**.

#### 2 – Configure `.env`

```bash
# Apple Developer credentials
APNS_KEY_ID=ABCDE12345          # 10-char Key ID
APNS_TEAM_ID=XYZAB67890         # 10-char Team ID
APNS_BUNDLE_ID=com.example.app  # App bundle identifier

# Full contents of the downloaded .p8 file (including header/footer lines)
APNS_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----

# Comma-separated list of APNs device tokens to receive notifications
APNS_DEVICE_TOKENS=<token1>,<token2>

# "true" → APNs sandbox (for development); "false" → production
APNS_SANDBOX=true

# Host port for the webhook service
WEBHOOK_PORT=8080
```

#### 3 – Configure a Grafana webhook contact point

1. In Grafana go to **Alerting → Contact points → New contact point**.
2. Choose type **Webhook** and set the URL to:
   ```
   http://notifications:8080/webhook
   ```
   (use `localhost` instead of `notifications` if Grafana is not in the
   same Docker network).
3. Save and assign the contact point to an alert rule.

### Endpoints

| Method | Path      | Description                              |
|--------|-----------|------------------------------------------|
| GET    | `/health` | Liveness probe – returns `{"status":"ok"}` |
| POST   | `/webhook`| Receive alert payload, send push notifications |

### File layout

```
notifications/
├── apns_client.py   # APNs HTTP/2 client (JWT auth)
├── webhook.py       # Flask webhook server
├── requirements.txt
└── Dockerfile
```


## Contributing

Contributions are always welcome!

