To start using MongoDB or PyMongo in your terminal, follow these steps:

## Starting MongoDB

### Install MongoDB
1. **Install MongoDB**:
   - **Windows**: Download the MongoDB installer from the [MongoDB Download Center](https://www.mongodb.com/try/download/community) and follow the installation instructions.
   - **macOS**: Use Homebrew:
     ```bash
     brew tap mongodb/brew
     brew install mongodb-community@<version>
     ```
   - **Linux**: Use your package manager (e.g., APT for Ubuntu):
     ```bash
     wget -qO - https://www.mongodb.org/static/pgp/server-<version>.asc | sudo apt-key add -
     echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/multiverse amd64/packages/  $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/mongodb-org-<version>.list
     sudo apt update
     sudo apt install -y mongodb-org
     ```

### Start MongoDB Server
2. **Start the MongoDB server**:
   - Run the following command in your terminal:
   ```bash
   mongod
   ```
   - This will start the MongoDB server. By default, it listens on port **27017**.

## Using the MongoDB Shell

3. **Open a new terminal window/tab**:
   - Use the MongoDB shell to interact with your database:
   ```bash
   mongo
   ```

## Running Your PyMongo Script

4. **Install PyMongo**:
   - Ensure you have PyMongo installed. If you haven't installed it yet, run:
   ```bash
   pip install pymongo python-dotenv
   ```

5. **Run your Python script**:
   - Assuming you’ve saved your code to a file (e.g., `database_operations.py`), you can run it like this:
   ```bash
   python database_operations.py
   ```

Make sure your MongoDB server is running before executing your Python script, as it needs to connect to the database.

### Verify Connection
After running your script, you should see printed messages indicating a successful connection or any connection failure errors.

If you need further customization, like setting different ports, modify the command you use to start MongoDB (`mongod --port <your_port>`).