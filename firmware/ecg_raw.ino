const int ECG_PIN = A0; 
const unsigned long SAMPLE_INTERVAL_US = 2000; // 500 Hz sampling rate (2000 microseconds)
unsigned long lastMicros = 0;

void setup() {
  Serial.begin(115200);
}

void loop() {
  unsigned long now = micros();
  if (now - lastMicros >= SAMPLE_INTERVAL_US) {
    lastMicros = now;
    int rawValue = analogRead(ECG_PIN);
    Serial.println(rawValue); // Stream data to laptop

  }
}