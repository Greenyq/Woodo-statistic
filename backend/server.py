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
import tempfile
import w3g
from urllib.parse import urljoin


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env', override=False)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create database indexes for performance (run once on startup)
async def create_database_indexes():
    """Create indexes for better query performance"""
    try:
        # Index for match_statuses collection
        await db.match_statuses.create_index("timestamp")
        await db.match_statuses.create_index("battle_tag")
        
        # TTL index to auto-delete old records after 7 days
        await db.match_statuses.create_index("timestamp", expireAfterSeconds=604800)
        
        logging.info("Database indexes created successfully")
    except Exception as e:
        logging.warning(f"Index creation warning: {str(e)}")  # Don't fail on index errors

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# W3Champions API base URL
W3C_API_BASE = "https://website-backend.w3champions.com/api"

# Define Models
class PlayerInput(BaseModel):
    battle_tag: str = Field(..., min_length=1)
    
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

class ReplayAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match_id: str
    player_battle_tag: str
    duration_seconds: int
    map_name: str
    winner: Optional[str] = None
    
    # Economy metrics
    apm: Optional[float] = None
    avg_gold_income: Optional[float] = None
    avg_wood_income: Optional[float] = None
    max_workers: Optional[int] = None
    
    # Build order analysis
    first_building_time: Optional[int] = None
    expansion_time: Optional[int] = None
    tech_buildings: List[Dict[str, int]] = []  # building_name -> time
    
    # Army composition
    units_produced: Dict[str, int] = {}
    units_lost: Dict[str, int] = {}
    
    # Strategic analysis
    strategy_type: Optional[str] = None  # "rush", "macro", "turtle", "cheese"
    aggression_level: Optional[float] = None  # 0.0 - 1.0
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PlayerReplayStats(BaseModel):
    battle_tag: str
    total_replays_analyzed: int
    avg_apm: Optional[float] = None
    favorite_strategy: Optional[str] = None
    economy_rating: Optional[float] = None  # 0.0 - 1.0
    aggression_rating: Optional[float] = None
    build_order_consistency: Optional[float] = None
    recent_analyses: List[ReplayAnalysis] = []

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

async def get_player_race_stats(battle_tag: str, gateway: int = 20, season: int = 23) -> Optional[Dict]:
    """Get player race statistics with detailed breakdown"""
    endpoint = f"players/{battle_tag}/race-stats?gateWay={gateway}&season={season}"
    return await get_w3c_data(endpoint)

async def get_player_hero_stats(battle_tag: str, season: int = 23) -> Optional[Dict]:
    """Get detailed hero statistics on maps vs races for a player"""
    endpoint = f"player-stats/{battle_tag}/hero-on-map-versus-race?season={season}"
    return await get_w3c_data(endpoint)

async def get_player_hero_stats_multi_season(battle_tag: str) -> Optional[Dict]:
    """Get hero statistics from both season 22 and 23 for better coverage"""
    season_23_stats = await get_player_hero_stats(battle_tag, 23)
    season_22_stats = await get_player_hero_stats(battle_tag, 22)
    
    if not season_23_stats and not season_22_stats:
        return None
    
    # Merge stats from both seasons
    merged_stats = {"heroStatsItemList": []}
    
    # Combine hero stats from both seasons
    hero_data = {}
    
    # Process season 23 data
    if season_23_stats and season_23_stats.get('heroStatsItemList'):
        for hero_stat in season_23_stats['heroStatsItemList']:
            hero_id = hero_stat.get('heroId')
            if hero_id:
                hero_data[hero_id] = hero_stat
    
    # Add season 22 data (merge if hero exists, add if not)
    if season_22_stats and season_22_stats.get('heroStatsItemList'):
        for hero_stat in season_22_stats['heroStatsItemList']:
            hero_id = hero_stat.get('heroId')
            if hero_id:
                if hero_id in hero_data:
                    # Merge stats (this is complex, for now just keep season 23 as primary)
                    pass
                else:
                    # Add hero from season 22 if not in season 23
                    hero_data[hero_id] = hero_stat
    
    merged_stats['heroStatsItemList'] = list(hero_data.values())
    return merged_stats

async def search_matches(battle_tag: str, offset: int = 0, page_size: int = 10, season: int = 23, gateway: int = 20) -> Optional[Dict]:
    """Search recent matches for a player using new API"""
    # URL encode the battle tag for the playerId parameter
    from urllib.parse import quote
    encoded_battle_tag = quote(battle_tag, safe='')
    endpoint = f"matches/search?playerId={encoded_battle_tag}&gateway={gateway}&offset={offset}&pageSize={page_size}&season={season}"
    return await get_w3c_data(endpoint)

async def get_recent_matches_smart(battle_tag: str, target_matches: int = 20) -> Optional[Dict]:
    """Get recent matches across seasons to reach target number of matches"""
    # Try current season (23) first
    season_23_matches = await search_matches(battle_tag, 0, target_matches, 23)
    
    if season_23_matches and season_23_matches.get('matches'):
        matches_23 = season_23_matches['matches']
        
        # If we have enough matches from season 23, return them
        if len(matches_23) >= target_matches:
            return {"matches": matches_23[:target_matches]}
        
        # If not enough matches, try to get more from season 22
        remaining_needed = target_matches - len(matches_23)
        season_22_matches = await search_matches(battle_tag, 0, remaining_needed, 22)
        
        if season_22_matches and season_22_matches.get('matches'):
            matches_22 = season_22_matches['matches']
            # Combine matches from both seasons
            all_matches = matches_23 + matches_22
            return {"matches": all_matches[:target_matches]}
        
        # Return what we have from season 23
        return {"matches": matches_23}
    
    # If no matches in season 23, try season 22
    season_22_matches = await search_matches(battle_tag, 0, target_matches, 22)
    if season_22_matches and season_22_matches.get('matches'):
        return {"matches": season_22_matches['matches'][:target_matches]}
    
    return None

async def download_replay_from_url(replay_url: str) -> Optional[bytes]:
    """Download replay file from URL"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(replay_url)
            if response.status_code == 200:
                return response.content
            else:
                logging.warning(f"Failed to download replay: {response.status_code}")
                return None
    except Exception as e:
        logging.error(f"Error downloading replay: {str(e)}")
        return None

def analyze_replay_file(replay_data: bytes, battle_tag: str) -> Optional[ReplayAnalysis]:
    """Analyze W3G replay file and extract strategic information"""
    try:
        # Save replay data to temporary file
        with tempfile.NamedTemporaryFile(suffix='.w3g', delete=False) as temp_file:
            temp_file.write(replay_data)
            temp_file_path = temp_file.name
        
        try:
            # Parse replay with w3g library
            replay = w3g.File(temp_file_path)
            
            # Basic match info
            match_info = replay.header
            duration = getattr(replay, 'duration', 0)
            map_name = getattr(match_info, 'map_name', 'Unknown')
            
            # Find player in replay
            player_data = None
            for player in getattr(replay, 'players', []):
                if hasattr(player, 'battle_tag') and player.battle_tag == battle_tag:
                    player_data = player
                    break
            
            if not player_data:
                logging.warning(f"Player {battle_tag} not found in replay")
                return None
            
            # Calculate APM
            apm = None
            try:
                if hasattr(replay, 'apm'):
                    apm_data = replay.apm()
                    if isinstance(apm_data, dict) and battle_tag in apm_data:
                        apm = apm_data[battle_tag]
                    elif isinstance(apm_data, (int, float)):
                        apm = float(apm_data)
            except Exception:
                pass
            
            # Analyze build order and strategy
            strategy_type = determine_strategy_type(replay, player_data)
            aggression_level = calculate_aggression_level(replay, player_data)
            
            # Create analysis result
            analysis = ReplayAnalysis(
                match_id=f"replay_{uuid.uuid4().hex[:8]}",
                player_battle_tag=battle_tag,
                duration_seconds=duration,
                map_name=map_name,
                apm=apm,
                strategy_type=strategy_type,
                aggression_level=aggression_level
            )
            
            return analysis
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        logging.error(f"Error analyzing replay: {str(e)}")
        return None

def determine_strategy_type(replay, player_data) -> str:
    """Determine player's strategy type based on replay analysis"""
    try:
        # This is a simplified analysis - in practice would need more sophisticated logic
        duration = getattr(replay, 'duration', 0)
        
        # Basic heuristics
        if duration < 300:  # Less than 5 minutes
            return "rush"
        elif duration < 600:  # 5-10 minutes  
            return "timing_attack"
        elif duration < 1200:  # 10-20 minutes
            return "macro"
        else:
            return "late_game"
            
    except Exception as e:
        logging.error(f"Error determining strategy: {str(e)}")
        return "unknown"

def calculate_aggression_level(replay, player_data) -> float:
    """Calculate player's aggression level (0.0 - 1.0)"""
    try:
        # Simplified calculation based on available data
        duration = getattr(replay, 'duration', 1)
        
        # Shorter games suggest more aggression
        if duration < 300:
            return 0.9
        elif duration < 600:
            return 0.7
        elif duration < 1200:
            return 0.5
        else:
            return 0.3
            
    except Exception as e:
        logging.error(f"Error calculating aggression: {str(e)}")
        return 0.5

async def analyze_player_replays(battle_tag: str, match_ids: List[str] = None) -> Optional[PlayerReplayStats]:
    """Analyze multiple replays for a player to build strategic profile"""
    try:
        # For now, we'll create a placeholder since we don't have direct replay URLs
        # In a real implementation, this would download and analyze actual replays
        
        analyses = []
        
        # Simulate some analysis results based on recent matches data
        recent_matches = await get_recent_matches_smart(battle_tag, 5)
        if recent_matches and recent_matches.get('matches'):
            for match in recent_matches['matches'][:3]:  # Analyze top 3 recent matches
                
                # Create simulated analysis based on match data
                duration = match.get('durationInSeconds', 600)
                map_name = match.get('map', 'Unknown')
                
                analysis = ReplayAnalysis(
                    match_id=str(match.get('id', uuid.uuid4())),
                    player_battle_tag=battle_tag,
                    duration_seconds=duration,
                    map_name=map_name,
                    apm=float(150 + (duration / 10)),  # Simulated APM
                    strategy_type=determine_strategy_type_from_duration(duration),
                    aggression_level=calculate_aggression_from_duration(duration)
                )
                analyses.append(analysis)
        
        if not analyses:
            return None
        
        # Calculate aggregate stats
        avg_apm = sum(a.apm for a in analyses if a.apm) / len([a for a in analyses if a.apm])
        
        strategy_counts = {}
        for analysis in analyses:
            if analysis.strategy_type:
                strategy_counts[analysis.strategy_type] = strategy_counts.get(analysis.strategy_type, 0) + 1
        
        favorite_strategy = max(strategy_counts.items(), key=lambda x: x[1])[0] if strategy_counts else "unknown"
        
        avg_aggression = sum(a.aggression_level for a in analyses if a.aggression_level) / len([a for a in analyses if a.aggression_level])
        
        # Calculate economy rating based on match patterns
        economy_rating = calculate_economy_rating(analyses)
        build_order_rating = calculate_build_order_consistency(analyses)
        
        player_stats = PlayerReplayStats(
            battle_tag=battle_tag,
            total_replays_analyzed=len(analyses),
            avg_apm=avg_apm if avg_apm else None,
            favorite_strategy=favorite_strategy,
            aggression_rating=avg_aggression if avg_aggression else None,
            economy_rating=economy_rating,
            build_order_consistency=build_order_rating,
            recent_analyses=analyses
        )
        
        return player_stats
        
    except Exception as e:
        logging.error(f"Error analyzing player replays: {str(e)}")
        return None

def determine_strategy_type_from_duration(duration: int) -> str:
    """Determine strategy type from match duration"""
    if duration < 300:
        return "rush"
    elif duration < 600:
        return "timing_attack"  
    elif duration < 1200:
        return "macro"
    else:
        return "late_game"

def calculate_aggression_from_duration(duration: int) -> float:
    """Calculate aggression level from match duration"""
    if duration < 300:
        return 0.9
    elif duration < 600:
        return 0.7
    elif duration < 1200:
        return 0.5
    else:
        return 0.3

def calculate_economy_rating(analyses: List[ReplayAnalysis]) -> float:
    """Calculate economy rating based on multiple factors"""
    if not analyses:
        return 0.5
    
    total_score = 0
    
    for analysis in analyses:
        score = 0.5  # Base score
        
        # APM factor (higher APM = better economy management)
        if analysis.apm:
            if analysis.apm >= 200:
                score += 0.3  # Excellent APM
            elif analysis.apm >= 120:
                score += 0.2  # Good APM
            elif analysis.apm >= 80:
                score += 0.1  # Average APM
            # Below 80 APM = no bonus
        
        # Game duration factor (optimal games show good economy)
        duration = analysis.duration_seconds
        if 600 <= duration <= 1200:  # 10-20 min = optimal economy games
            score += 0.1
        elif duration > 1800:  # Very long games = good late economy
            score += 0.15
        elif duration < 300:  # Very short = poor economy development
            score -= 0.1
            
        # Strategy factor
        if analysis.strategy_type == "macro":
            score += 0.1  # Macro players typically have better economy
        elif analysis.strategy_type == "rush":
            score -= 0.05  # Rush players focus less on economy
            
        # Ensure score stays in valid range
        score = max(0.0, min(1.0, score))
        total_score += score
    
    return total_score / len(analyses)

def calculate_build_order_consistency(analyses: List[ReplayAnalysis]) -> float:
    """Calculate build order consistency based on strategy patterns"""
    if not analyses:
        return 0.5
    
    # Count strategy types
    strategy_counts = {}
    for analysis in analyses:
        if analysis.strategy_type:
            strategy_counts[analysis.strategy_type] = strategy_counts.get(analysis.strategy_type, 0) + 1
    
    if not strategy_counts:
        return 0.5
    
    # More consistent if player sticks to fewer strategies
    total_games = len(analyses)
    most_common_count = max(strategy_counts.values())
    consistency = most_common_count / total_games
    
    # Bonus for having a clear preference (>60% same strategy)
    if consistency >= 0.6:
        consistency = min(1.0, consistency + 0.1)
    
    return consistency

def get_hero_to_units_mapping():
    """Map heroes to their typical unit compositions"""
    return {
        # Human heroes
        "archmage": {
            "primary_units": ["footman", "rifleman", "sorceress", "priest"],
            "secondary_units": ["knight", "spell_breaker"],
            "strategy_focus": "caster_heavy"
        },
        "mountainking": {
            "primary_units": ["footman", "rifleman", "knight"],
            "secondary_units": ["mortar_team", "flying_machine"],
            "strategy_focus": "melee_heavy"
        },
        "paladin": {
            "primary_units": ["footman", "knight", "priest"],
            "secondary_units": ["rifleman", "spell_breaker"],
            "strategy_focus": "heal_tank"
        },
        "bloodmage": {
            "primary_units": ["footman", "spell_breaker", "phoenix"],
            "secondary_units": ["knight", "sorceress"],
            "strategy_focus": "anti_caster"
        },
        
        # Orc heroes
        "blademaster": {
            "primary_units": ["grunt", "raider", "wind_rider"],
            "secondary_units": ["troll_headhunter", "kodo_beast"],
            "strategy_focus": "mobility_harass"
        },
        "farseer": {
            "primary_units": ["grunt", "troll_headhunter", "spirit_walker"],
            "secondary_units": ["raider", "wind_rider"],
            "strategy_focus": "caster_support"
        },
        "taurenchieftain": {
            "primary_units": ["grunt", "troll_headhunter", "tauren"],
            "secondary_units": ["kodo_beast", "wind_rider"],
            "strategy_focus": "heavy_melee"
        },
        "shadowhunter": {
            "primary_units": ["troll_headhunter", "wind_rider", "troll_witch_doctor"],
            "secondary_units": ["grunt", "spirit_walker"],
            "strategy_focus": "ranged_caster"
        },
        
        # Night Elf heroes
        "demonhunter": {
            "primary_units": ["archer", "huntress", "dryad"],
            "secondary_units": ["druid_of_the_claw", "ballista"],
            "strategy_focus": "ranged_kite"
        },
        "keeperofthegrove": {
            "primary_units": ["archer", "druid_of_the_claw", "dryad"],
            "secondary_units": ["huntress", "druid_of_the_talon"],
            "strategy_focus": "nature_summon"
        },
        "priestessofthemoon": {
            "primary_units": ["archer", "huntress", "druid_of_the_talon"],
            "secondary_units": ["dryad", "ballista"],
            "strategy_focus": "owl_scout"
        },
        "warden": {
            "primary_units": ["huntress", "druid_of_the_claw", "chimera"],
            "secondary_units": ["archer", "mountain_giant"],
            "strategy_focus": "stealth_ambush"
        },
        
        # Undead heroes
        "deathknight": {
            "primary_units": ["ghoul", "crypt_fiend", "necromancer"],
            "secondary_units": ["abomination", "meat_wagon"],
            "strategy_focus": "unholy_swarm"
        },
        "lich": {
            "primary_units": ["skeleton", "necromancer", "banshee"],
            "secondary_units": ["crypt_fiend", "frost_wyrm"],
            "strategy_focus": "undead_mass"
        },
        "dreadlord": {
            "primary_units": ["ghoul", "crypt_fiend", "destroyer"],
            "secondary_units": ["gargoyle", "abomination"],
            "strategy_focus": "air_superiority"
        },
        "cryptlord": {
            "primary_units": ["crypt_fiend", "carrion_beetle", "necromancer"],
            "secondary_units": ["ghoul", "destroyer"],
            "strategy_focus": "bug_swarm"
        }
    }

def analyze_unit_composition_vs_race(hero_stats: dict, opponent_race: str, target_race: str = None) -> dict:
    """Analyze what units opponent typically uses based on hero picks"""
    if not hero_stats or not hero_stats.get('heroStatsItemList'):
        return None
    
    hero_unit_mapping = get_hero_to_units_mapping()
    unit_predictions = {}
    strategy_focus_counts = {}
    
    # Analyze each hero the opponent uses
    for hero_stat in hero_stats['heroStatsItemList']:
        hero_id = hero_stat.get('heroId', '').lower()
        
        # Get hero usage stats
        total_games = 0
        for stat in hero_stat.get('stats', []):
            overall_map = None
            for map_stat in stat.get('winLossesOnMap', []):
                if map_stat.get('map') == 'Overall':
                    overall_map = map_stat
                    break
            
            if overall_map:
                for wl in overall_map.get('winLosses', []):
                    total_games += wl.get('games', 0)
        
        # Skip heroes with very few games
        if total_games < 3:
            continue
        
        # Map hero to units
        if hero_id in hero_unit_mapping:
            hero_data = hero_unit_mapping[hero_id]
            
            # Weight by games played
            weight = min(total_games / 10, 1.0)  # Max weight at 10+ games
            
            # Add primary units
            for unit in hero_data['primary_units']:
                unit_predictions[unit] = unit_predictions.get(unit, 0) + (weight * 0.8)
            
            # Add secondary units  
            for unit in hero_data['secondary_units']:
                unit_predictions[unit] = unit_predictions.get(unit, 0) + (weight * 0.3)
            
            # Track strategy focus
            focus = hero_data['strategy_focus']
            strategy_focus_counts[focus] = strategy_focus_counts.get(focus, 0) + weight
    
    if not unit_predictions:
        return None
    
    # Sort units by likelihood
    sorted_units = sorted(unit_predictions.items(), key=lambda x: x[1], reverse=True)
    
    # Get most likely strategy focus
    most_likely_focus = max(strategy_focus_counts.items(), key=lambda x: x[1])[0] if strategy_focus_counts else "balanced"
    
    return {
        "predicted_units": sorted_units[:6],  # Top 6 most likely units
        "strategy_focus": most_likely_focus,
        "confidence": min(sum(unit_predictions.values()) / 3, 1.0),  # Confidence based on data amount
        "counter_recommendations": get_counter_units(sorted_units[:3], opponent_race, target_race)
    }

def get_counter_units(enemy_units: list, enemy_race: str, your_race: str = None) -> list:
    """Get recommended counter units based on enemy composition"""
    counter_mapping = {
        # Counters for common units
        "footman": ["archer", "crypt_fiend", "troll_headhunter"],
        "rifleman": ["huntress", "ghoul", "raider"],
        "sorceress": ["spell_breaker", "destroyer", "banshee"],
        "knight": ["crypt_fiend", "spear_thrower", "pike_man"],
        
        "grunt": ["archer", "rifleman", "huntress"],
        "troll_headhunter": ["footman", "ghoul", "huntress"],
        "raider": ["rifleman", "archer", "crypt_fiend"],
        "wind_rider": ["rifleman", "archer", "gargoyle"],
        
        "archer": ["footman", "grunt", "ghoul"],
        "huntress": ["rifleman", "troll_headhunter", "crypt_fiend"],
        "druid_of_the_claw": ["crypt_fiend", "destroyer", "mortar_team"],
        
        "ghoul": ["rifleman", "archer", "huntress"],
        "crypt_fiend": ["knight", "tauren", "mountain_giant"],
        "necromancer": ["spell_breaker", "destroyer", "druid_of_the_talon"],
        "abomination": ["archer", "crypt_fiend", "ballista"]
    }
    
    counter_recommendations = []
    for unit_name, _ in enemy_units:
        if unit_name in counter_mapping:
            counter_recommendations.extend(counter_mapping[unit_name])
    
    # Remove duplicates and return top counters
    unique_counters = list(dict.fromkeys(counter_recommendations))
    return unique_counters[:4]

def format_unit_name(unit_name: str) -> str:
    """Format unit names for display"""
    unit_display_names = {
        "footman": "👤 Пехотинец",
        "rifleman": "🔫 Стрелок", 
        "sorceress": "✨ Чародейка",
        "knight": "🐎 Рыцарь",
        "priest": "⛪ Жрец",
        "spell_breaker": "🛡️ Разрушитель",
        
        "grunt": "⚔️ Пехотинец",
        "troll_headhunter": "🏹 Охотник",
        "raider": "🐺 Рейдер",
        "wind_rider": "🦅 Летун",
        "tauren": "🐂 Таурен",
        
        "archer": "🏹 Лучница",
        "huntress": "🌙 Охотница",
        "druid_of_the_claw": "🐻 Друид Когтя",
        "dryad": "🧚 Дриада",
        "mountain_giant": "⛰️ Гигант",
        
        "ghoul": "🧟 Упырь",
        "crypt_fiend": "🕷️ Склепный",
        "necromancer": "☠️ Некромант",
        "abomination": "🤢 Мерзость",
        "banshee": "👻 Банши"
    }
    
    return unit_display_names.get(unit_name, f"⚔️ {unit_name.replace('_', ' ').title()}")

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

def determine_match_result(match_data: dict, player_battle_tag: str) -> dict:
    """Determine if player won the match and extract hero info from new API format"""
    if not match_data.get('teams'):
        return {"won": None, "heroUsed": None, "map": match_data.get("mapName", "Unknown")}
    
    # Find which team the player was on and if they won
    player_team_won = None
    hero_used = None
    
    for team in match_data['teams']:
        for player in team.get('players', []):
            if player.get('battleTag') == player_battle_tag:
                player_team_won = team.get('won', False)
                hero_used = player.get('heroId', 'Unknown')
                break
        if player_team_won is not None:
            break
    
    return {
        "won": player_team_won,
        "heroUsed": hero_used,
        "map": match_data.get("mapName", "Unknown"),
        "durationInSeconds": match_data.get("durationInSeconds", 0)
    }

def analyze_player_achievements(basic_stats: dict, hero_stats: dict, recent_matches: dict, player_race: str = None, player_battle_tag: str = None) -> list:
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
                        "description": f"Основной герой: {main_hero} ({games_count} игр)",
                        "type": "hero",
                        "color": "blue"
                    })
    
    # 2. WIN/LOSS STREAK ACHIEVEMENTS  
    if recent_matches and recent_matches.get('matches') and player_battle_tag:
        matches = recent_matches['matches']
        if len(matches) >= 3:
            # Check for win/loss streaks from most recent matches
            streak_count = 0
            streak_type = None
            
            # Count consecutive wins or losses from the beginning
            for match in matches:
                match_result = determine_match_result(match, player_battle_tag)
                won = match_result.get('won')
                
                if won is None:  # Skip matches where result is unclear
                    continue
                    
                if streak_type is None:
                    streak_type = won
                    streak_count = 1
                elif streak_type == won:
                    streak_count += 1
                else:
                    break
            
            if streak_count >= 5:
                if streak_type:  # Win streak
                    achievements.append({
                        "title": "🚀 Неудержимый!",
                        "description": f"{streak_count} побед подряд - легенда!",
                        "type": "streak",
                        "color": "purple"
                    })
                else:  # Loss streak  
                    achievements.append({
                        "title": "💀 Катастрофа",
                        "description": f"{streak_count} поражений подряд - кошмар!",
                        "type": "streak", 
                        "color": "red"
                    })
            elif streak_count >= 3:
                if streak_type:  # Win streak
                    achievements.append({
                        "title": "🔥 Я в огне!",
                        "description": f"{streak_count} побед подряд",
                        "type": "streak",
                        "color": "red"
                    })
                else:  # Loss streak
                    achievements.append({
                        "title": "😤 Это все интернет!",
                        "description": f"{streak_count} поражения подряд", 
                        "type": "streak",
                        "color": "gray"
                    })
            elif streak_count == 2:
                if streak_type:
                    achievements.append({
                        "title": "🎯 На волне",
                        "description": "2 победы подряд",
                        "type": "streak", 
                        "color": "yellow"
                    })
                else:
                    achievements.append({
                        "title": "😠 Невезет",
                        "description": "2 поражения подряд",
                        "type": "streak",
                        "color": "yellow"
                    })
    
    # 3. ACTIVITY ACHIEVEMENTS  
    from datetime import datetime, timezone, timedelta
    
    if recent_matches and recent_matches.get('matches') and len(recent_matches['matches']) > 0:
        matches = recent_matches['matches']
        matches_count = len(matches)
        
        # Analyze timestamps to determine recent activity patterns
        now = datetime.now(timezone.utc)
        today = now.date()
        yesterday = today - timedelta(days=1)
        last_week = now - timedelta(days=7)
        
        # Count matches in different time periods
        today_matches = 0
        yesterday_matches = 0
        week_matches = 0
        
        for match in matches:
            # Try to parse match timestamp - the API might have different field names
            match_time = None
            for time_field in ['startTime', 'timestamp', 'createdAt', 'endTime']:
                if time_field in match and match[time_field]:
                    try:
                        # Handle different timestamp formats
                        time_str = match[time_field]
                        if isinstance(time_str, str):
                            if 'T' in time_str:
                                # ISO format
                                match_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                            else:
                                # Try parsing as timestamp
                                match_time = datetime.fromtimestamp(float(time_str), tz=timezone.utc)
                        elif isinstance(time_str, (int, float)):
                            # Unix timestamp
                            match_time = datetime.fromtimestamp(time_str, tz=timezone.utc)
                        break
                    except (ValueError, TypeError):
                        continue
            
            if match_time:
                match_date = match_time.date()
                if match_date == today:
                    today_matches += 1
                elif match_date == yesterday:
                    yesterday_matches += 1
                    
                if match_time >= last_week:
                    week_matches += 1
        
        # Determine activity level based on timestamp analysis
        if today_matches >= 5:
            achievements.append({
                "title": "🎮 Игроман",
                "description": f"{today_matches} игр сегодня - не можешь оторваться!",
                "type": "activity",
                "color": "blue"
            })
        elif today_matches >= 2:
            achievements.append({
                "title": "🔥 В игре",
                "description": f"{today_matches} игры сегодня - в форме",
                "type": "activity",
                "color": "green"
            })
        elif today_matches == 1:
            achievements.append({
                "title": "🌅 Начинаю день",
                "description": "1 игра сегодня",
                "type": "activity",
                "color": "green"
            })
        elif yesterday_matches > 0:
            achievements.append({
                "title": "🌙 Вчерашний боец",
                "description": f"Последняя активность вчера ({yesterday_matches} игр)",
                "type": "activity",
                "color": "yellow"
            })
        elif week_matches > 0:
            achievements.append({
                "title": "🎯 Разминка",
                "description": f"{week_matches} игр на этой неделе",
                "type": "activity",
                "color": "yellow"
            })
        else:
            # Fall back to simple count if no timestamps available
            if matches_count >= 10:
                achievements.append({
                    "title": "🎮 Игроман",
                    "description": f"{matches_count} игр недавно - активный игрок",
                    "type": "activity",
                    "color": "blue"
                })
            elif matches_count >= 5:
                achievements.append({
                    "title": "🔥 В игре", 
                    "description": f"{matches_count} игр недавно - в форме",
                    "type": "activity",
                    "color": "green"
                })
            elif matches_count >= 2:
                achievements.append({
                    "title": "🌅 Начинаю день",
                    "description": f"{matches_count} игры недавно",
                    "type": "activity",
                    "color": "green"
                })
            else:  # 1 match
                achievements.append({
                    "title": "🎯 Разминка",
                    "description": "1 игра недавно",
                    "type": "activity",
                    "color": "yellow"
                })
    else:
        # No recent matches - player is inactive
        achievements.append({
            "title": "😴 Только проснулся", 
            "description": "Нет недавних игр",
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
        # Calculate race distribution balance
        race_games = {}
        total_games = 0
        race_names_map = {1: "Human", 2: "Orc", 4: "Night Elf", 8: "Undead", 0: "Random"}
        
        for wl in basic_stats['winLosses']:
            games = wl.get('games', 0)
            if games >= 5:  # Only count races with at least 5 games
                race_num = wl.get('race', 0)
                race_name = race_names_map.get(race_num, f"Race_{race_num}")
                race_games[race_name] = games
                total_games += games
        
        if len(race_games) >= 3 and total_games >= 50:  # Minimum requirements
            # Check if races are balanced (within 20-30% of each other)
            max_games = max(race_games.values())
            min_games = min(race_games.values())
            
            # Calculate if distribution is balanced (max race shouldn't be more than 150% of min race)
            balance_ratio = min_games / max_games if max_games > 0 else 0
            
            if balance_ratio >= 0.5:  # Within 50% range = balanced enough
                achievements.append({
                    "title": "🌈 Мульти-рейсер",
                    "description": f"Сбалансированная игра за {len(race_games)} рас ({total_games} игр)",
                    "type": "diversity",
                    "color": "yellow"
                })
            elif len(race_games) >= 4:
                # Has many races but not balanced
                achievements.append({
                    "title": "🎭 Экспериментатор", 
                    "description": f"Пробует разные расы: {len(race_games)} рас",
                    "type": "diversity",
                    "color": "blue"
                })
        elif len(race_games) == 1:
            # Specialist - plays only one race
            main_race = list(race_games.keys())[0]
            main_games = race_games[main_race]
            achievements.append({
                "title": "🎯 Специалист",
                "description": f"Играет только за {main_race} ({main_games} игр)",
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
    
    # 7. ECONOMIC ACHIEVEMENTS (based on game patterns)
    if recent_matches and recent_matches.get('matches') and player_battle_tag:
        matches = recent_matches['matches']
        if len(matches) > 0:
            recent_match = matches[0]  # Most recent match
            match_result = determine_match_result(recent_match, player_battle_tag)
            duration = match_result.get('durationInSeconds', 0)
            
            if duration > 0:
                # Estimate economic performance based on game duration and result
                won = match_result.get('won', False)
                
                # Short wins suggest good economy (rush/fast expand success)
                if duration < 600 and won:  # Less than 10 minutes and won
                    achievements.append({
                        "title": "💰 Экономический гений",
                        "description": "Быстрая победа - отличная экономика",
                        "type": "economy",
                        "color": "green"
                    })
                # Very long losses suggest poor economy
                elif duration > 1800 and not won:  # More than 30 minutes and lost
                    achievements.append({
                        "title": "💸 Не умеет добывать",
                        "description": "Долгое поражение - слабая экономика", 
                        "type": "economy",
                        "color": "red"
                    })
                # Long wins suggest good late game economy
                elif duration > 1200 and won:  # More than 20 minutes and won
                    achievements.append({
                        "title": "🏦 Скупердяй",
                        "description": "Долгая победа - накопил ресурсы",
                        "type": "economy", 
                        "color": "blue"
                    })
                # Short losses suggest poor early economy
                elif duration < 480 and not won:  # Less than 8 minutes and lost
                    achievements.append({
                        "title": "💔 Бомж",
                        "description": "Быстрое поражение - нет экономики",
                        "type": "economy",
                        "color": "red"
                    })
                # Medium duration games
                elif 600 <= duration <= 1200:
                    if won:
                        achievements.append({
                            "title": "⚖️ Сбалансированный",
                            "description": "Стабильная экономика",
                            "type": "economy",
                            "color": "green"
                        })
            
            # Special economy achievements based on multiple matches
            if len(matches) >= 5:
                # Check if player consistently wins short games (good economy)
                short_wins = 0
                long_losses = 0
                
                for m in matches[:5]:
                    match_result = determine_match_result(m, player_battle_tag)
                    duration = match_result.get('durationInSeconds', 0)
                    won = match_result.get('won')
                    
                    if won is not None:  # Only count matches where we can determine the result
                        if duration < 600 and won:
                            short_wins += 1
                        elif duration > 1200 and not won:
                            long_losses += 1
                
                if short_wins >= 3:
                    achievements.append({
                        "title": "⚡ Экономический раш",
                        "description": "Мастер быстрой экономики",
                        "type": "economy",
                        "color": "yellow"
                    })
                
                if long_losses >= 3:
                    achievements.append({
                        "title": "🐌 Медленно копит",
                        "description": "Слабая поздняя экономика",
                        "type": "economy", 
                        "color": "red"
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
        
        # Find opponents (players that are not the queried player)
        for team in match_data.get("teams", []):
            for player in team.get("players", []):
                if player.get("battleTag") != battle_tag:
                    opponent_tag = player.get("battleTag")
                    if opponent_tag:
                        # Get comprehensive opponent statistics
                        opponent_basic_stats = await get_player_statistics(opponent_tag)
                        opponent_race_stats = await get_player_race_stats(opponent_tag)
                        opponent_matches = await get_recent_matches_smart(opponent_tag, 20)
                        opponent_hero_stats = await get_player_hero_stats_multi_season(opponent_tag)
                        
                        # Analyze achievements
                        opponent_race = get_race_name(player.get("race", 16))
                        opponent_achievements = analyze_player_achievements(
                            opponent_basic_stats, 
                            opponent_hero_stats, 
                            opponent_matches,
                            opponent_race,
                            opponent_tag
                        )
                        
                        # Analyze replays for strategic insights
                        replay_analysis = await analyze_player_replays(opponent_tag)
                        
                        # TODO: Analyze unit composition preferences (implement later)
                        # unit_analysis = analyze_unit_composition_vs_race(opponent_hero_stats, opponent_race)
                        
                        opponents.append({
                            "battle_tag": opponent_tag,
                            "race": get_race_name(player.get("race", 16)),
                            "basic_stats": opponent_basic_stats,
                            "race_stats": opponent_race_stats,
                            "recent_matches": opponent_matches,
                            "hero_stats": opponent_hero_stats,
                            "achievements": opponent_achievements,
                            "replay_analysis": replay_analysis.dict() if replay_analysis else None
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
        matches = await get_recent_matches_smart(battle_tag, 50)
        
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
        opponent_matches = await get_recent_matches_smart(demo_battle_tag, 20)
        
        # Use real recent matches with multi-season hero data
        opponent_hero_stats = await get_player_hero_stats_multi_season(demo_battle_tag)
        
        # Analyze achievements
        opponent_achievements = analyze_player_achievements(
            opponent_basic_stats, 
            opponent_hero_stats, 
            opponent_matches,
            "Night Elf",  # Siberia#21832 is Night Elf main
            demo_battle_tag
        )
        
        # Analyze replays for strategic insights
        replay_analysis = await analyze_player_replays(demo_battle_tag)
        
        # TODO: Analyze unit composition (implement later)
        # unit_analysis = analyze_unit_composition_vs_race(opponent_hero_stats, "Night Elf")
        
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
                            "achievements": opponent_achievements,
                            "replay_analysis": replay_analysis.dict() if replay_analysis else None
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

@api_router.get("/replay-analysis/{battle_tag}")
async def get_replay_analysis(battle_tag: str):
    """Get replay analysis for a player"""
    try:
        replay_stats = await analyze_player_replays(battle_tag)
        
        if not replay_stats:
            return {
                "battle_tag": battle_tag,
                "analysis": None,
                "message": "No replay analysis available"
            }
        
        return {
            "battle_tag": battle_tag,
            "analysis": replay_stats.dict(),
            "message": "Replay analysis completed"
        }
        
    except Exception as e:
        logging.error(f"Error getting replay analysis for {battle_tag}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting replay analysis: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    """Initialize database indexes on startup"""
    await create_database_indexes()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()