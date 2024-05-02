import hashlib
import configparser
from datetime import datetime, date, timedelta
from contextlib import contextmanager
from bot.utils.messages import info_message, trial_message
from bot.models import Base, User, Settings, Variables, Strategies
from bot.db.database import DBSession, engine

# Base.metadata.drop_all(engine)
Base.metadata.create_all(bind=engine)
config = configparser.ConfigParser()
config.read('settings/config.ini', encoding="utf-8")

secret_key = config.get("settings", "secret_key")


def generate_hashed_token(bot_id):
    return hashlib.md5(secret_key.encode() + bot_id.encode()).hexdigest()


def check_hashed_token(bot_id, hashed_token):
    return hashed_token == generate_hashed_token(bot_id)


def set_expiration_date(user, **kwargs):
    date_string = datetime.today().strftime("%m/%d/%Y, %H:%M:%S")
    start_date = datetime.strptime(date_string, "%m/%d/%Y, %H:%M:%S")
    user.created_at = start_date
    expire_date = start_date + timedelta(**kwargs)
    user.expire_in = expire_date
    return user


@contextmanager
def session_scope():
    session = DBSession()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


class UserController(object):
    model = User
    settings = Settings
    variables = Variables
    strategies = Strategies

    def create(self, data):
        with session_scope() as session:
            user = session.query(self.model).filter_by(user_bot=data["user"]["user_bot"]).first()
            if not user:
                check_email_in_use = session.query(self.model).filter_by(email=data["user"]["email"]).first()
                if check_email_in_use:
                    print("Email já está em uso...")
                    return {"result": False, "message": "Email já está em uso..."}
                user = self.model()
                user.user_bot = int(data["user"]["user_bot"])
                user.email = data["user"]["email"]
                user.name = data["user"].get("name")
                user.password = data["user"]["password"]
                user.account_type = data["user"]["account_type"]
                user.game_type = data["user"]["game_type"]
                user.token = data["user"]["token"]
                user.wallet = data["user"]["wallet"]
                self.save(session, user, refresh=True)
                if data.get("strategies"):
                    self.create_user_strategies(session, data, user.id)
                self.create_user_variables(session, data, user.id)
                self.create_user_settings(session, data, user.id)
            else:
                self.update(session, data, user)
            return {"user": user.as_dict(),
                    "settings": user.settings[0].as_dict(),
                    "variables": user.variables[0].as_dict(),
                    "strategies": [strategy.as_dict() for strategy in user.strategies]
                    }

    def check_user_exists(self, bot_id):
        with session_scope() as session:
            user = session.query(self.model).filter_by(user_bot=bot_id).first()
            if not user:
                return False
            elif user.expire_in and datetime.now() > user.expire_in:
                return self.change_token_status(user.id)
            return {"user": user.as_dict(),
                    "settings": user.settings[0].as_dict() if len(user.settings) > 0 else None,
                    "variables": user.variables[0].as_dict() if len(user.variables) > 0 else None,
                    "strategies": [strategy.as_dict() for strategy in user.strategies]
                    if len(user.strategies) > 0 else None
                    }

    def create_user_settings(self, session, data, user_id=None):
        if not user_id:
            user_id = data["settings"].get("owner_id") if data["settings"] else data["user"]["id"]
        user_settings = session.query(self.settings).filter_by(owner_id=user_id).first()
        if not user_settings:
            user_settings = self.settings(**data["settings"], owner_id=user_id)
        else:
            user_settings.strategy_type = data["settings"].get("strategy_type")
            user_settings.enter_type = data["settings"].get("enter_type")
            user_settings.enter_percent = data["settings"].get("enter_percent")
            user_settings.enter_value = data["settings"].get("enter_value")
            user_settings.first_amount = data["settings"].get("first_amount")
            user_settings.stop_type = data["settings"].get("stop_type")
            user_settings.stop_gain = data["settings"].get("stop_gain")
            user_settings.stop_loss = data["settings"].get("stop_loss")
            user_settings.protection_hand = data["settings"].get("protection_hand")
            user_settings.protection_value = data["settings"].get("protection_value")
            user_settings.martingale = data["settings"].get("martingale")
            user_settings.white_martingale = data["settings"].get("white_martingale")
            user_settings.martingale_multiplier = data["settings"].get("martingale_multiplier")
            user_settings.white_multiplier = data["settings"].get("white_multiplier")
            user_settings.quantity_cycles = data["settings"].get("quantity_cycles")
        self.save(session, user_settings, refresh=True)
        return user_settings

    def create_user_variables(self, session, data, user_id=None):
        if not user_id:
            user_id = data["variables"].get("owner_id") if data["variables"] else data["user"]["id"]
        user_variables = session.query(self.variables).filter_by(owner_id=user_id).first()
        if not user_variables:
            user_variables = self.variables(**data["variables"], owner_id=user_id)
        else:
            user_variables.count_loss = data["variables"].get("count_loss")
            user_variables.count_win = data["variables"].get("count_win")
            user_variables.count_martingale = data["variables"].get("count_martingale")
            user_variables.profit = data["variables"].get("profit")
            user_variables.balance = data["variables"].get("balance")
            user_variables.first_balance = data["variables"].get("first_balance")
            user_variables.created = data["variables"].get("created")
            user_variables.is_gale = data["variables"].get("is_gale")
        self.save(session, user_variables, refresh=True)
        return user_variables

    def create_user_strategies(self, session, data, user_id=None):
        user_strategies = None
        if not user_id:
            user_id = data["user"]["id"]
        if data["strategies"] and len(data["strategies"]) > 0:
            for index, strategy in enumerate(data["strategies"]):
                if not strategy.get("id"):
                    user_strategies = self.strategies(**strategy, owner_id=user_id)
                else:
                    user_strategies = session.query(self.strategies).filter_by(id=strategy["id"],
                                                                               owner_id=user_id).first()
                    if user_strategies:
                        user_strategies.sequence = strategy["sequence"]
                        user_strategies.color = strategy["color"]
                self.save(session, user_strategies, refresh=True)
        return user_strategies

    def read(self):
        with session_scope() as session:
            users = session.query(self.model).all()
            if len(users) > 0:
                return [{"user": user.as_dict(),
                         "settings": user.settings[0].as_dict() if len(user.settings) > 0 else None,
                         "variables": user.variables[0].as_dict() if len(user.variables) > 0 else None,
                         "strategies": [strategy.as_dict() for strategy in user.strategies]
                         if len(user.strategies) > 0 else None} for index, user in enumerate(users)][::-1]

    def update(self, session, data, user):
        check_email_in_use = session.query(self.model).filter_by(email=data["user"]["email"]).first()
        user.user_bot = data["user"].get("user_bot")
        user.email = data["user"].get("email")
        user.name = data["user"].get("name")
        user.password = data["user"].get("password")
        user.account_type = data["user"].get("account_type")
        user.game_type = data["user"].get("game_type")
        user.already_tested = data["user"].get("already_tested")
        user.is_testing = data["user"].get("is_testing")
        user.token = data["user"].get("token")
        user.hashed_token = data["user"].get("hashed_token")
        user.wallet = data["user"].get("wallet")
        user.color_bet = data["user"].get("color_bet")
        user.color_before = data["user"].get("color_before")
        user.point_bet = data["user"].get("point_bet")
        user.point_before = data["user"].get("point_before")
        user.is_betting = data["user"].get("is_betting")
        user.payment_id = data["user"].get("payment_id")
        user.payment_status = data["user"].get("payment_status")
        user.payment_expire_in = data["user"].get("payment_expire_in")
        if not check_email_in_use:
            self.save(session, user, refresh=True)
        if data.get("strategies"):
            self.create_user_strategies(session, data)
        self.create_user_variables(session, data)
        self.create_user_settings(session, data)

    def enable(self, data):
        with session_scope() as session:
            user = session.query(self.model).filter_by(user_bot=data["user"]["user_bot"]).first()
            if user:
                user.is_active = data["user"]["is_active"]
                user.process_pid = data["user"]["process_pid"]
                user.settings[0].first_amount = data["settings"].get("enter_value")
                user.settings[0].first_protection = data["settings"].get("protection_value")
                self.create_user_strategies(session, data, user.id)
                self.create_user_settings(session, data, user.id)
                self.create_user_variables(session, data, user.id)
                self.save(session, user, refresh=True)

    def change_bets_status(self, data):
        with session_scope() as session:
            user = session.query(self.model).filter_by(user_bot=data["user"]["user_bot"]).first()
            if user:
                user.is_betting = data["user"]["is_betting"]
                self.save(session, user)

    def change_payment_status(self, data):
        with session_scope() as session:
            if data["user"].get("email"):
                user = session.query(self.model).filter_by(email=data["user"]["email"]).first()
                if user:
                    user.payment_status = data["user"]["payment_status"]
                    self.save(session, user)
            else:
                user = session.query(self.model).filter_by(payment_id=data["user"]["payment_id"]).first()
                hashed_token = generate_hashed_token(str(user.user_bot)) if user.payment_status != "PAID" else None
                user.payment_status = data["user"]["payment_status"]
                if user.payment_status == "PAID" and user.payment_expire_in:
                    set_expiration_date(user, **{"days": int(user.payment_expire_in)})
                info_message(user, hashed_token)
                user.payment_id = None
                user.payment_expire_in = None
                user.is_testing = False
            self.save(session, user)

    def create_trial_access(self, data, **kwargs):
        with session_scope() as session:
            user = session.query(self.model).filter_by(user_bot=data["user"]["user_bot"]).first()
            if user:
                user.already_tested = True
                user.is_testing = True
                user.hashed_token = generate_hashed_token(str(user.user_bot))
                set_expiration_date(user, **kwargs)
                trial_message(user, kwargs)
            self.save(session, user)
            return {"user": user.as_dict(),
                    "settings": user.settings[0].as_dict() if len(user.settings) > 0 else None,
                    "variables": user.variables[0].as_dict() if len(user.variables) > 0 else None,
                    "strategies": [strategy.as_dict() for strategy in user.strategies]
                    if len(user.strategies) > 0 else None
                    }

    def change_token_status(self, uid, client_id=None, days=None):
        with session_scope() as session:
            user = session.query(self.model).filter_by(id=int(uid)).first()
            if client_id:
                user = session.query(self.model).filter_by(user_bot=int(client_id)).first()
            if user:
                hashed_token = generate_hashed_token(str(user.user_bot)) \
                    if user.payment_status != "PAID" and not user.is_testing else None
                user.payment_status = "PAID" if user.payment_status != "PAID" and not user.is_testing else "PENDING"
                if user.already_tested:
                    user.is_testing = False
                if user.is_active:
                    user.is_active = False
                    user.is_betting = False
                if not hashed_token:
                    user.hashed_token = hashed_token
                    data = {"user": user.as_dict(),
                            "settings": user.settings[0].as_dict() if len(user.settings) > 0 else None,
                            "variables": user.variables[0].as_dict() if len(user.variables) > 0 else None,
                            "strategies": [strategy.as_dict() for strategy in user.strategies]
                            if len(user.strategies) > 0 else None
                            }
                    if data:
                        self.disable(data)
                if user.payment_status == "PAID" and days:
                    set_expiration_date(user, **{"days": int(days)})
                else:
                    user.created_at = None
                    user.expire_in = None
                    if user.already_tested:
                        user.is_testing = False
                info_message(user, hashed_token)
                self.save(session, user)
            return {"user": user.as_dict(),
                    "settings": user.settings[0].as_dict() if len(user.settings) > 0 else None,
                    "variables": user.variables[0].as_dict() if len(user.variables) > 0 else None,
                    "strategies": [strategy.as_dict() for strategy in user.strategies]
                    if len(user.strategies) > 0 else None
                    }

    def disable(self, data):
        with session_scope() as session:
            user = session.query(self.model).filter_by(user_bot=data["user"]["user_bot"]).first()
            if user:
                user.is_active = data["user"]["is_active"]
                user.is_betting = data["user"]["is_betting"]
                user.color_bet = data["user"]["color_bet"]
                user.color_before = data["user"]["color_before"]
                self.create_user_strategies(session, data, user.id)
                self.create_user_settings(session, data, user.id)
                self.create_user_variables(session, data, user.id)
                self.save(session, user)

    def delete(self, uid):
        with session_scope() as session:
            user = session.query(self.model).filter_by(id=int(uid)).first()
            if user:
                self.save(session, user, delete=True)
        return self.read()

    def delete_all_trial(self):
        with session_scope() as session:
            session.query(self.model).filter_by(hashed_token=None).delete()
            session.commit()
        return self.read()

    def delete_strategies(self, data, index):
        with session_scope() as session:
            user_strategy = session.query(self.strategies).filter_by(id=data["strategies"][index]["id"],
                                                                     owner_id=data["user"]["id"]
                                                                     ).first()
        if user_strategy:
            self.save(session, user_strategy, delete=True)

    @staticmethod
    def save(session, object_model, delete=False, refresh=False):
        try:
            if delete:
                session.delete(object_model)
            else:
                session.add(object_model)
            session.flush()
            session.commit()
            if refresh:
                session.refresh(object_model)
        except:
            session.rollback()
            raise
