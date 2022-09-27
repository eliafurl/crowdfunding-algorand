# Crowdfunding platform development

## Folder structure
- contracts: contains folders for different types of contracts (e.g. counter: example contract; crowdfunding: actual folder for crowdfunding contracts).
- build: contains build artifacts e.g. *.teal and *.json files.
- main_*.py: python main for testing the contracts. 

## HOW TO
1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Install [Algorand sandbox](https://github.com/algorand/sandbox)
3. Add this project folder as bind volume in sandbox `docker-compose.yml` under key `services.algod`:
    ```yml
    volumes:
      - type: bind
        source: <path>
        target: /data
    ```
4. Start sandbox:
    ```txt
    $ ./sandbox up
    ```
5. Install Python virtual environment in project folder:
    ```txt
    $ python3 -m venv venv
    $ source ./venv/Scripts/activate # Windows
    $ source ./venv/bin/activate # Linux / MacOS
    ```
5. Install dependencies in virtual environment:
    ```txt
    $ pip3 install -r requirements.txt
    ```


## HOW TO
* Export TEAL and ABI:
    ```txt
    python3 /path/to/contract.py
    ```
* Compile, deploy and test contracts:
    ```txt
    python3 main_<contract>.py
    ```