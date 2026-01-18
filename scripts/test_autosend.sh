#!/bin/bash

messages=(
  "Where is my order?"
  "Can you send me my tracking number?"
  "How do I update the firmware on my Apollo II?"
  "I want a refund"
  "This product does not work"
)

for msg in "${messages[@]}"; do
  echo "----------------------------------------"
  echo "MESSAGE: $msg"
  python ai/auto_send_classifier.py "$msg"
done
