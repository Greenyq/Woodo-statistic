from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import httpx
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import re


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# W3Champions API base URL
W3C_API_BASE = "https://website-backend.w3champions.com/api"

# Define Models
class PlayerInput(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=50)
    battle_tag: str = Field(..., min_length=1)
    race: str = Field(..., pattern="^(Human|Orc|Night Elf|Undead|Random)$")
    
    @validator('battle_tag')
    def validate_battle_tag(cls, v):
        # Updated regex to support Cyrillic characters and more international characters
        if not re.match(r'^[\w\u0400-\u04FF\u0500-\u052F]+#\d{4,5}$', v, re.UNICODE):
            raise ValueError('Battle tag must be in format PlayerName#1234 (supports international characters)')
        return v

class MatchStatus(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    battle_tag: str
    is_in_game: bool = False
    match_data: Optional[Dict[Any, Any]] = None
    opponent_data: Optional[Dict[Any, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OpponentStats(BaseModel):
    battle_tag: str
    race: int
    wins: int
    losses: int
    winrate: float
    mmr: Optional[int] = None
    hero_stats: List[Dict[str, Any]] = []
    recent_matches: List[Dict[str, Any]] = []

# W3Champions API client
async def get_w3c_data(endpoint: str) -> Optional[Dict]:
    """Fetch data from W3Champions API"""
    try:
        # URL encode the endpoint to handle special characters like #
        from urllib.parse import quote
        if "#" in endpoint:
            # Split endpoint and encode battle tag part
            parts = endpoint.split("/")
            for i, part in enumerate(parts):
                if "#" in part:
                    parts[i] = quote(part, safe='')
            endpoint = "/".join(parts)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{W3C_API_BASE}/{endpoint}")
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return None  # No content (e.g., player not in game)
            else:
                logging.warning(f"W3C API returned {response.status_code} for {endpoint}")
                return None
    except Exception as e:
        logging.error(f"Error fetching W3C data from {endpoint}: {str(e)}")
        return None

async def check_ongoing_match(battle_tag: str) -> Optional[Dict]:
    """Check if player is in an ongoing match"""
    endpoint = f"matches/ongoing/{battle_tag}"
    return await get_w3c_data(endpoint)

async def get_player_statistics(battle_tag: str) -> Optional[Dict]:
    """Get player statistics"""
    endpoint = f"players/{battle_tag}"
    return await get_w3c_data(endpoint)

async def get_player_race_stats(battle_tag: str, gateway: int = 20, season: int = 22) -> Optional[Dict]:
    """Get player race statistics with detailed breakdown"""
    endpoint = f"players/{battle_tag}/race-stats?gateWay={gateway}&season={season}"
    return await get_w3c_data(endpoint)

async def get_player_hero_stats(battle_tag: str, season: int = 22) -> Optional[Dict]:
    """Get detailed hero statistics on maps vs races for a player"""
    endpoint = f"player-stats/{battle_tag}/hero-on-map-versus-race?season={season}"
    return await get_w3c_data(endpoint)

async def search_matches(battle_tag: str, offset: int = 0, page_size: int = 10) -> Optional[Dict]:
    """Search recent matches for a player"""
    endpoint = f"matches/search?playername={battle_tag}&offset={offset}&pageSize={page_size}"
    return await get_w3c_data(endpoint)

def get_race_number(race_name: str) -> int:
    """Convert race name to W3C race number"""
    race_map = {
        "Human": 1,
        "Orc": 2,
        "Night Elf": 4,
        "Undead": 8,
        "Random": 16
    }
    return race_map.get(race_name, 16)

def get_race_name(race_number: int) -> str:
    """Convert W3C race number to race name"""
    race_map = {
        1: "Human",
        2: "Orc", 
        4: "Night Elf",
        8: "Undead",
        16: "Random"
    }
    return race_map.get(race_number, "Unknown")

def analyze_player_achievements(basic_stats: dict, hero_stats: dict, recent_matches: dict, player_race: str = None) -> list:
    """Analyze player data and return list of achievements/badges"""
    achievements = []
    
    # 1. HERO MAIN ACHIEVEMENTS
    if hero_stats and hero_stats.get('heroStatsItemList'):
        # Find most played hero by total games
        hero_games = {}
        for hero_stat in hero_stats['heroStatsItemList']:
            total_games = 0
            for stat in hero_stat.get('stats', []):
                for map_stat in stat.get('winLossesOnMap', []):
                    if map_stat.get('map') == 'Overall':
                        for win_loss in map_stat.get('winLosses', []):
                            total_games += win_loss.get('games', 0)
            if total_games > 0:
                hero_games[hero_stat['heroId']] = total_games
        
        # Hero-specific achievements
        # Map heroes to races for filtering
        heroes_by_race = {
            "Human": ["archmage", "mountainking", "paladin", "bloodmage"],
            "Orc": ["blademaster", "farseer", "taurenchieftain", "shadowhunter"], 
            "Night Elf": ["demonhunter", "keeperofthegrove", "moonpriestess", "warden", "bansheeranger"],
            "Undead": ["deathknight", "dreadlord", "lich", "cryptlord"],
            "Random": []  # Random can use any heroes
        }
        
        hero_achievements = {
            "demonhunter": "🦸 Я и есть демон хантер",
            "blademaster": "🥷 Мастер бамбука", 
            "mountainking": "⛵ Горный корабль",
            "archmage": "🧙 Мастер магии",
            "paladin": "⚔️ Светлый рыцарь",
            "bloodmage": "🩸 Кровавый маг",
            "farseer": "👁️ Дальновидец",
            "taurenchieftain": "🐂 Вождь племени",
            "shadowhunter": "🏹 Охотник теней",
            "keeperofthegrove": "🌳 Хранитель рощи",
            "moonpriestess": "🌙 Лунная жрица",
            "warden": "🦉 Стражница",
            "bansheeranger": "👻 Банши-рейнджер",
            "deathknight": "💀 Коил и ты труп",
            "dreadlord": "👹 Повелитель ужаса",
            "lich": "❄️ Король-лич",
            "cryptlord": "🕷️ Повелитель склепов"
        }
        
        # Filter heroes by player's race
        valid_heroes = heroes_by_race.get(player_race, [])
        if player_race == "Random":
            valid_heroes = list(hero_achievements.keys())  # Random can use all heroes
        
        # Filter hero games by player's race
        if hero_games and valid_heroes:
            # Only consider heroes of the player's race
            filtered_hero_games = {hero: games for hero, games in hero_games.items() 
                                 if hero in valid_heroes or player_race == "Random"}
            
            if filtered_hero_games:
                main_hero = max(filtered_hero_games, key=filtered_hero_games.get)
                games_count = filtered_hero_games[main_hero]
                
                if main_hero in hero_achievements and games_count >= 10:
                    achievements.append({
                        "title": hero_achievements[main_hero],
                        "description": f"Основной герой {player_race}: {games_count} игр",
                        "type": "hero",
                        "color": "blue"
                    })
    
    # 2. WIN/LOSS STREAK ACHIEVEMENTS  
    if recent_matches and recent_matches.get('matches'):
        matches = recent_matches['matches']
        if len(matches) >= 3:
            # Check last 3 matches for streaks
            last_3 = [match.get('won', False) for match in matches[:3]]
            
            if all(last_3):  # 3 wins in a row
                achievements.append({
                    "title": "🔥 Я в огне!",
                    "description": "3 победы подряд",
                    "type": "streak",
                    "color": "red"
                })
            elif not any(last_3):  # 3 losses in a row
                achievements.append({
                    "title": "😤 Это все интернет!",
                    "description": "3 поражения подряд", 
                    "type": "streak",
                    "color": "gray"
                })
    
    # 3. ACTIVITY ACHIEVEMENTS
    if recent_matches and recent_matches.get('matches'):
        from datetime import datetime, timezone, timedelta
        today = datetime.now(timezone.utc).date()
        
        # Check if player played today (if we had match timestamps)
        # For now, if no recent matches, assume inactive
        if len(recent_matches['matches']) == 0:
            achievements.append({
                "title": "😴 Только проснулся",
                "description": "Давно не играл",
                "type": "activity", 
                "color": "yellow"
            })
    
    # 4. SKILL & EXPERIENCE ACHIEVEMENTS
    if basic_stats and basic_stats.get('winLosses'):
        total_wins = sum(wl.get('wins', 0) for wl in basic_stats['winLosses'])
        total_games = sum(wl.get('games', 0) for wl in basic_stats['winLosses']) 
        
        if total_games > 0:
            winrate = total_wins / total_games
            
            # Experience-based achievements
            if total_games >= 1000:
                achievements.append({
                    "title": "👑 Ветеран",
                    "description": f"{total_games} игр сыграно",
                    "type": "experience", 
                    "color": "purple"
                })
            elif total_games >= 500:
                achievements.append({
                    "title": "🎖️ Опытный боец",
                    "description": f"{total_games} игр сыграно",
                    "type": "experience",
                    "color": "blue"
                })
            
            # Skill-based achievements  
            if winrate >= 0.75 and total_games >= 100:
                achievements.append({
                    "title": "💎 Легенда",
                    "description": f"Винрейт {int(winrate * 100)}% в {total_games} играх",
                    "type": "skill",
                    "color": "purple"
                })
            elif winrate >= 0.6 and total_games >= 50:
                achievements.append({
                    "title": "⭐ Мастер",
                    "description": f"Винрейт {int(winrate * 100)}%",
                    "type": "skill", 
                    "color": "blue"
                })
            elif winrate <= 0.35 and total_games >= 50:
                achievements.append({
                    "title": "😅 Учусь играть",
                    "description": f"Винрейт {int(winrate * 100)}%, но не сдаюсь!",
                    "type": "spirit",
                    "color": "green"
                })
    
    # 5. RACE DIVERSITY ACHIEVEMENTS
    if basic_stats and basic_stats.get('winLosses'):
        races_played = [wl for wl in basic_stats['winLosses'] if wl.get('games', 0) >= 10]
        if len(races_played) >= 4:
            achievements.append({
                "title": "🌈 Мульти-рейсер",
                "description": f"Играет за {len(races_played)} рас",
                "type": "diversity",
                "color": "yellow"
            })
        elif len(races_played) == 1:
            # Find the main race
            main_race_num = races_played[0]['race']
            race_names = {1: "Human", 2: "Orc", 4: "Night Elf", 8: "Undead", 0: "Random"}
            race_name = race_names.get(main_race_num, "Unknown")
            achievements.append({
                "title": "🎯 Специалист",
                "description": f"Играет только за {race_name}",
                "type": "focus",
                "color": "blue"
            })
    
    # 6. FUN PERSONALITY ACHIEVEMENTS (based on patterns)
    if recent_matches and recent_matches.get('matches'):
        matches = recent_matches['matches']
        if len(matches) >= 5:
            # Check average game duration (if available)
            durations = [match.get('durationInSeconds', 0) for match in matches[:5] if match.get('durationInSeconds')]
            if durations:
                avg_duration = sum(durations) / len(durations)
                if avg_duration < 300:  # Less than 5 minutes
                    achievements.append({
                        "title": "⚡ Блицкригер",
                        "description": "Быстрые игры в среднем",
                        "type": "playstyle",
                        "color": "red"
                    })
                elif avg_duration > 1800:  # More than 30 minutes  
                    achievements.append({
                        "title": "🐌 Стратег",
                        "description": "Долгие обдуманные игры",
                        "type": "playstyle", 
                        "color": "blue"
                    })
    
    return achievements

# Routes
@api_router.get("/")
async def root():
    return {"message": "W3Champions Match Scout API"}

@api_router.post("/check-match")
async def check_player_match(player_input: PlayerInput):
    """Check if player is currently in a match and get opponent info"""
    try:
        battle_tag = player_input.battle_tag
        
        # Check if player is in ongoing match
        match_data = await check_ongoing_match(battle_tag)
        
        if not match_data:
            # Player not in match
            match_status = MatchStatus(
                battle_tag=battle_tag,
                is_in_game=False
            )
            
            # Store status in database
            await db.match_statuses.insert_one(match_status.dict())
            return {
                "status": "not_in_game", 
                "message": "Player is not currently in a match",
                "data": match_status.dict()
            }
        
        # Player is in match - extract opponent info
        opponents = []
        player_race_num = get_race_number(player_input.race)
        
        # Find opponents (players that are not the queried player)
        for team in match_data.get("teams", []):
            for player in team.get("players", []):
                if player.get("battleTag") != battle_tag:
                    opponent_tag = player.get("battleTag")
                    if opponent_tag:
                        # Get comprehensive opponent statistics
                        opponent_basic_stats = await get_player_statistics(opponent_tag)
                        opponent_race_stats = await get_player_race_stats(opponent_tag)
                        opponent_matches = await search_matches(opponent_tag, 0, 20)
                        opponent_hero_stats = await get_player_hero_stats(opponent_tag)
                        
                        # Analyze achievements
                        opponent_achievements = analyze_player_achievements(
                            opponent_basic_stats, 
                            opponent_hero_stats, 
                            opponent_matches
                        )
                        
                        opponents.append({
                            "battle_tag": opponent_tag,
                            "race": get_race_name(player.get("race", 16)),
                            "basic_stats": opponent_basic_stats,
                            "race_stats": opponent_race_stats,
                            "recent_matches": opponent_matches,
                            "hero_stats": opponent_hero_stats,
                            "achievements": opponent_achievements
                        })
        
        match_status = MatchStatus(
            battle_tag=battle_tag,
            is_in_game=True,
            match_data=match_data,
            opponent_data={"opponents": opponents}
        )
        
        # Store status in database
        await db.match_statuses.insert_one(match_status.dict())
        
        return {
            "status": "in_game",
            "message": "Player is currently in a match",
            "data": match_status.dict()
        }
        
    except Exception as e:
        logging.error(f"Error checking match for {player_input.battle_tag}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking match status: {str(e)}")

@api_router.get("/player-stats/{battle_tag}")
async def get_player_stats(battle_tag: str):
    """Get detailed player statistics"""
    try:
        stats = await get_player_statistics(battle_tag)
        matches = await search_matches(battle_tag, 0, 50)
        
        return {
            "battle_tag": battle_tag,
            "statistics": stats,
            "recent_matches": matches
        }
    except Exception as e:
        logging.error(f"Error getting player stats for {battle_tag}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting player statistics: {str(e)}")

@api_router.get("/match-history")
async def get_match_history():
    """Get stored match check history"""
    try:
        match_statuses = await db.match_statuses.find().sort("timestamp", -1).limit(50).to_list(50)
        # Convert ObjectId to string for JSON serialization
        for status in match_statuses:
            if "_id" in status:
                status["_id"] = str(status["_id"])
        return {"match_history": match_statuses}
    except Exception as e:
        logging.error(f"Error getting match history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting match history: {str(e)}")

@api_router.get("/demo-match")
async def get_demo_match():
    """Get demo match data with real W3Champions statistics"""
    try:
        # Use real player with actual stats - Multi-race example
        demo_battle_tag = "Siberia#21832"
        
        # Get real opponent statistics
        opponent_basic_stats = await get_player_statistics(demo_battle_tag)
        opponent_race_stats = await get_player_race_stats(demo_battle_tag)
        opponent_matches = await search_matches(demo_battle_tag, 0, 10)
        opponent_hero_stats = await get_player_hero_stats(demo_battle_tag)
        
        # Analyze achievements
        opponent_achievements = analyze_player_achievements(
            opponent_basic_stats, 
            opponent_hero_stats, 
            opponent_matches
        )
        
        demo_match_data = {
            "status": "in_game",
            "message": f"Demo match found! Player DemoPlayer#1234 vs {demo_battle_tag}",
            "data": {
                "id": "demo-match-real",
                "battle_tag": "DemoPlayer#1234",
                "is_in_game": True,
                "match_data": {
                    "id": "demo-match-real",
                    "map": "ConcealedHill",
                    "matchType": "1v1"
                },
                "opponent_data": {
                    "opponents": [
                        {
                            "battle_tag": demo_battle_tag,
                            "race": "Night Elf",
                            "basic_stats": opponent_basic_stats,
                            "race_stats": opponent_race_stats,
                            "recent_matches": opponent_matches,
                            "hero_stats": opponent_hero_stats,
                            "achievements": opponent_achievements
                        }
                    ]
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        return demo_match_data
        
    except Exception as e:
        logging.error(f"Error getting demo match: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting demo match: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()