## Config files for setting up mongodb with docker compose on a VM
the `.env_template` file is a template -- for running mongodb with docker-compose, assign the `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD` vars to `.env_template` and rename it to `.env`. Then run `docker-compose up` to get everything going.
