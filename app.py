from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///poker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Player(db.Model):
    PlayerId = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100), nullable=False, unique=True)


class Event(db.Model):
    EventId = db.Column(db.Integer, primary_key=True)
    Date = db.Column(db.String(100), nullable=False)
    HostName = db.Column(db.String(100), db.ForeignKey('player.Name'), nullable=False)


class Game(db.Model):
    GameId = db.Column(db.Integer, primary_key=True)
    EventId = db.Column(db.Integer, db.ForeignKey('event.EventId'), nullable=False)


class PlayersInGame(db.Model):
    EventId = db.Column(db.Integer, primary_key=True)
    GameId = db.Column(db.Integer, primary_key=True)
    PlayerName = db.Column(db.String(100), primary_key=True)
    IsActive = db.Column(db.Boolean, nullable=False)
    Position = db.Column(db.String(10))
    Points = db.Column(db.Integer)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['EventId', 'GameId'],
            ['game.EventId', 'game.GameId'],
        ),
        db.ForeignKeyConstraint(
            ['PlayerName'],
            ['player.Name'],
        ),
    )


@app.context_processor
def utility_processor():
    return dict(enumerate=enumerate)


@app.route('/')
def leaderboard():
    leaderboard_data = db.session.query(
        Player.Name,
        db.func.count(PlayersInGame.GameId).label('NumberOfGames'),
        db.func.sum(PlayersInGame.Points).label('SumOfPoints'),
        (db.func.sum(PlayersInGame.Points) / db.func.count(PlayersInGame.GameId)).label('AvgPoints')
    ).join(PlayersInGame, Player.Name == PlayersInGame.PlayerName) \
        .filter(PlayersInGame.IsActive == True) \
        .group_by(Player.Name) \
        .order_by(db.desc('SumOfPoints')).all()

    return render_template('index.html', leaderboard_data=leaderboard_data)


@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    if request.method == 'POST':
        date = request.form['date']
        host_name = request.form['host_name']
        if date and host_name:
            if not db.session.query(Event).filter_by(Date=date, HostName=host_name).first():
                new_event = Event(Date=date, HostName=host_name)
                db.session.add(new_event)
                db.session.commit()
                return redirect(url_for('add_event'))
    players = Player.query.all()
    events = Event.query.all()
    return render_template('add_event.html', players=players, events=events)


@app.route('/add_game', methods=['GET', 'POST'])
def add_game():
    if request.method == 'POST':
        event_id = request.form['event_id']
        active_players = request.form.getlist('active_players')
        winner = request.form['winner']
        runner_up = request.form['runner_up']

        new_game = Game(EventId=event_id)
        db.session.add(new_game)
        db.session.commit()

        game_id = new_game.GameId

        for player in active_players:
            position = 'n.a.'
            points = 0
            if player == winner:
                position = '1'
                points = 3
            elif player == runner_up:
                position = '2'
                points = 1
            new_players_in_game = PlayersInGame(EventId=event_id, GameId=game_id, PlayerName=player, IsActive=True,
                                                Position=position, Points=points)
            db.session.add(new_players_in_game)

        db.session.commit()
        return redirect(url_for('add_game'))

    events = Event.query.all()
    players = Player.query.all()
    most_recent_event = db.session.query(Event).order_by(Event.Date.desc()).first()
    return render_template('add_game.html', events=events, players=players, most_recent_event=most_recent_event)


@app.route('/add_player', methods=['GET', 'POST'])
def add_player():
    if request.method == 'POST':
        name = request.form['name']
        if name and not db.session.query(Player).filter_by(Name=name).first():
            new_player = Player(Name=name)
            db.session.add(new_player)
            db.session.commit()
            return redirect(url_for('add_player'))
    players = Player.query.all()
    return render_template('add_player.html', players=players)


@app.route('/view_results')
def view_results():
    results = db.session.query(
        Event.Date,
        Event.HostName,
        Game.GameId,
        db.func.max(db.case((PlayersInGame.Position == '1', PlayersInGame.PlayerName), else_=None)).label('Winner'),
        db.func.max(db.case((PlayersInGame.Position == '2', PlayersInGame.PlayerName), else_=None)).label('RunnerUp')
    ).join(Game, Event.EventId == Game.EventId) \
        .join(PlayersInGame, (Game.EventId == PlayersInGame.EventId) & (Game.GameId == PlayersInGame.GameId)) \
        .group_by(Event.Date, Event.HostName, Game.GameId) \
        .order_by(Event.Date).all()

    return render_template('view_results.html', results=results)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)