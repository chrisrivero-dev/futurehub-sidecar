# Flashing Your SD Card

Your Apollo Full Node’s entire operating system runs on a small industrial **Micro SD card** located on the bottom of the device.

You may need to reflash this card to:

- Reset your device to a stock state
- Fix corruption caused by power outages or prolonged use

⚠️ **Important:** This process must be performed on a **separate computer or laptop**.

---

## ⚠️ Data Warning (Read First)

**All data on the Micro SD card will be erased.**

This includes:

- Files in your desktop or home folder
- Wallet files
- Any locally saved data

Before proceeding:

- Back up important files, **or**
- Move them to the SSD drive on your Apollo

---

## Step 1: Download the Correct SD Card Image

Download the latest SD card image from the official FutureBit image releases page:

**Apollo OS Releases / SD Card Image Download**

### Image selection notes

- **All Apollo II devices** use the image named:  
  **Apollo II / BTC MCU2**
- **Apollo BTC devices** may require either an **MCU1** or **MCU2** image

To determine which Apollo BTC version you have, use:
**Apollo BTC MCU1 / MCU2 Identification**

> The image files are large (nearly 2 GB). Download time may vary.

---

## Step 2: (Optional) Verify the Download

You may verify the **SHA-256 checksum** to ensure the download was not corrupted.  
This is optional, but recommended if you experience flashing issues.

---

## Step 3: Install Etcher

Download **Etcher**, the recommended flashing tool:

- https://www.etcher.io

⚠️ **Important Update:**  
Recent versions of Etcher have issues with compressed files.

- If your image file ends in `.img.xz`, **decompress it first**
- Use the `.img` file when selecting the image in Etcher

---

## Step 4: Shut Down the Apollo

1. Use the shutdown option from the Apollo menu
2. Wait until the fan spins at full speed
3. Once the fan spins high, power off the rear power switch

---

## Step 5: Remove the Micro SD Card

- The SD card is located on the **bottom of the device**
- It sits next to the SSD drive in the silver slot on the blue controller board
- Press the card in until you feel a click — it will pop out slightly

⚠️ The slot is tight.  
Using **tweezers** is recommended so the card does not drop inside the case.

---

## Step 6: Insert the SD Card Into Your Computer

- Insert the card into your computer’s SD slot, **or**
- Use a USB-to-MicroSD adapter (typically $5–$10)

If your computer reports the card as unreadable, **ignore this** — it is formatted for a different operating system.

---

## Step 7: Flash the Image Using Etcher

1. Launch **Etcher**
2. Click **Flash from File**
3. Select the downloaded `.img` file
4. Choose the **16 GB SD card** as the target
5. Click **Flash**

Etcher will handle the flashing and verification process.

---

## Step 8: Finish and Reinstall

- Wait for Etcher to confirm the flash was successful
- Your computer may still report the card as unreadable — this is **normal**
- Eject the SD card safely

Reinsert the SD card into the Apollo:

- Push until you hear or feel a **click**
- Power on the device

The Apollo should boot into the updated operating system.

⚠️ You will need to **set up the device again** after flashing.

---

**Source:**  
https://www.futurebit.io/flashing-sd-card  
**Trust Tier:** Tier 1 (Official FutureBit Support)  
**Auto-send Eligible:** Yes
