// server.js  (Express version)
import express from 'express';
import dotenv  from 'dotenv';
dotenv.config();                      

const app = express();
app.use(express.static('.'));       

// tiny endpoint the browser will fetch once:
app.get('/config.json', (_, res) => {
  res.json({
    deviceUid   : process.env.PI_DEVICE_UID,
    mqttHost    : process.env.MQTT_HOST,
    mqttPort    : Number(process.env.MQTT_PORT || 8884),
    mqttPath    : process.env.MQTT_PATH || '/mqtt',
    mqttUsername: process.env.MQTT_USERNAME,
    mqttPassword: process.env.MQTT_PASSWORD,
    stunUrls    : ['stun:stun.l.google.com:19302'],
    // turnUrl     : process.env.TURN_URL,
    // turnUsername: process.env.TURN_USER,
    // turnPassword: process.env.TURN_PASS,
  });
});

app.listen(8080, () =>
  console.log('HTTP server on http://localhost:8080')
);
