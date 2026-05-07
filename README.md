## PakRemit

In this PakRemit project my effort is to build and practice a proper well designed fintech ecosystem. Coming to the why of this project then friend the thing is, in Pakistan and many other developing markets, the digital payments and the global remittances handling is often a big challenge. Like People often face problems like their money getting stuck in the middle of a transfer or even the systems not working when they need them the most. Also in this project I am using different domains of logic means overall payment handling with consistency which platforms like Stripe mainly do, the distribution consistency which platforms like Uber do, and the database sharding use for the data separation which is mainly done by the platforms liek Monzo.

## Tech Stack

# Core:
Django / Django REST Framework (DRF)
PostgreSQL (7 Separate Databases)
Service Layer Architecture

# Async & Distributed Logic:
Redis 
Celery & Celery Beat (Background tasks & retries)
Process Operator logic

# Security & Auth:
JWT
HMAC Signatures
Device Fingerprinting & SHA-256 Hashing

# Advanced Engineering:
Multi-Database Routers
Horizontal Sharding
Event Sourcing logic
Distributed Tracing
Circuit Breakers 

# Important Stats:
According to recent reports, Pakistan receives nearly $30 Billion in remittances every year from overseas, mainly from overseas pakistani's. And the thing is this do support our countries overall economy quite a much. Therefore in order to keep learning I am building this project and it will help me design a system which can handle thousands of people securely sending/sharing money at the same time.

# Things to Learn:
In my last project for the first time I used concpets like database sharding and circuit breakers, so now on this project I am gonna re practice those concepts to use them correclty and also at the same time I am gonna and learn try and learn some new concepts, so following are the main concepts which are going to be used in this project:

- Event Sourcing:
See normally while working in an app for example, we just overwrite a number like => balance = 5000. But in this PakRemit project, I am gonna learn the concept of "Event Sourcing." And this means we save every single thing that happened as an event and wich cant be changed. Like it’s a record that cant be edited or deleted, and this is how mainly the real banks work.

- Advanced Database Sharding:
In this projet I am gonna use much complex form of sharding logic. Like I am gonna use the Horizontal Sharding for wallets which is based on the User IDs and the Time based Sharding for the transactions purposes.

- Circuit Breakers:
I am gonna use this concept as well to handle the failures correctly.

- Distributed Tracing:
This features is about keeping the track of like how the requests are working across the different services.

# Key Features:
- The Immutable Record
- Idempotency Protection
- Smart Forex Handling
- Automatic Settlements
- Webhook Retry System
- KYC & Biometric