import bcrypt
print(bcrypt.hashpw("Aditya@123".encode(), bcrypt.gensalt()).decode())
