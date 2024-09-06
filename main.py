from bottle import Bottle, request, response, run
from sqlalchemy.orm import Session
from config import SessionLocal, engine
from models import Base, User, Organization, Member, Role
import bcrypt
import jwt
import datetime

app = Bottle()
Base.metadata.create_all(bind=engine)
SECRET_KEY = 'my_secret_key'

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post('/signup')
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    org_name = data.get('organization_name')
    
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        db = next(get_db())

        # Check if the user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            response.status = 400
            return {'error': 'User already exists'}

        new_user = User(email=email, password=hashed_pw)
        db.add(new_user)
        db.commit()

        new_org = Organization(name=org_name, status="Active")
        db.add(new_org)
        db.commit()

        owner_role = Role(name="tenant", org_id=new_org.id)
        db.add(owner_role)
        db.commit()

        new_member = Member(org_id=new_org.id, user_id=new_user.id, role_id=owner_role.id)
        db.add(new_member)
        db.commit()

        response.status = 201
        return {'message': 'User and organization created successfully'}
    except Exception as e:
        db.rollback()
        response.status = 400
        return {'error': str(e)}
    
@app.post('/signin')
def signin():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    try:
        db = next(get_db())

        user = db.query(User).filter(User.email == email).first()

        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            token = jwt.encode({
                'user_id': user.id,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
            }, SECRET_KEY, algorithm='HS256')
            return {'token': token}
        else:
            response.status = 401
            return {'error': 'Invalid email or password'}
    except Exception as e:
        response.status = 400
        return {'error': str(e)}

@app.post('/reset-password')
def reset_password():
    data = request.json
    email = data.get('email')
    new_password = data.get('new_password')

    hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

    try:
        db = next(get_db())

        user = db.query(User).filter(User.email == email).first()
        if not user:
            response.status = 404
            return {'error': 'User not found'}

        user.password = hashed_pw
        db.commit()

        response.status = 200
        return {'message': 'Password reset successfully'}
    except Exception as e:
        db.rollback()
        response.status = 400
        return {'error': str(e)}

@app.post('/invite-member')
def invite_member():
    data = request.json
    org_id = data.get('org_id')
    email = data.get('email')
    role_id = data.get('role_id')

    try:
        db = next(get_db())

        user = db.query(User).filter(User.email == email).first()
        if not user:
            response.status = 404
            return {'error': 'User not found'}

        new_member = Member(org_id=org_id, user_id=user.id, role_id=role_id)
        db.add(new_member)
        db.commit()

        response.status = 200
        return {'message': 'Member invited successfully'}
    except Exception as e:
        db.rollback()
        response.status = 400
        return {'error': str(e)}

# Delete Member
@app.delete('/delete-member')
def delete_member():
    data = request.json
    org_id = data.get('org_id')
    user_id = data.get('user_id')

    try:
        db = next(get_db())

        member = db.query(Member).filter(Member.org_id == org_id, Member.user_id == user_id).first()
        if not member:
            response.status = 404
            return {'error': 'Member not found'}

        db.delete(member)
        db.commit()

        response.status = 200
        return {'message': 'Member deleted successfully'}
    except Exception as e:
        db.rollback()
        response.status = 400
        return {'error': str(e)}

# Update Member Role
@app.put('/update-member-role')
def update_member_role():
    data = request.json
    org_id = data.get('org_id')
    user_id = data.get('user_id')
    role_id = data.get('role_id')

    try:
        db = next(get_db())

        member = db.query(Member).filter(Member.org_id == org_id, Member.user_id == user_id).first()
        if not member:
            response.status = 404
            return {'error': 'Member not found'}

        member.role_id = role_id
        db.commit()

        response.status = 200
        return {'message': 'Member role updated successfully'}
    except Exception as e:
        db.rollback()
        response.status = 400
        return {'error': str(e)}

# Run the app
if __name__ == '__main__':
    run(app, host='localhost', port=8080, debug=True)
