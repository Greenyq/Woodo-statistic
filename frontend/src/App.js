import React, { useState, useEffect, useRef } from "react";
import "@/App.css";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
// Select component replaced with native HTML select
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Sword, Trophy, Target, User, Clock, Shield } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [playerData, setPlayerData] = useState({
    nickname: "",
    battle_tag: "",
    race: ""
  });
  
  // Add refs for direct DOM manipulation as fallback
  const nicknameRef = useRef(null);
  const battleTagRef = useRef(null);
  const raceRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [matchStatus, setMatchStatus] = useState(null);
  const [error, setError] = useState("");
  const [lastChecked, setLastChecked] = useState(null);
  const [autoMonitoring, setAutoMonitoring] = useState(false);
  const [intervalId, setIntervalId] = useState(null);

  const races = [
    { value: "Human", label: "Human", icon: "⚔️" },
    { value: "Orc", label: "Orc", icon: "🪓" },
    { value: "Night Elf", label: "Night Elf", icon: "🏹" },
    { value: "Undead", label: "Undead", icon: "💀" },
    { value: "Random", label: "Random", icon: "🎲" }
  ];

  const handleInputChange = (field, value) => {
    console.log('Form change:', field, value);
    setPlayerData(prev => {
      const newData = { ...prev, [field]: value };
      console.log('New player data:', newData);
      return newData;
    });
    setError("");
  };

  const validateBattleTag = (battleTag) => {
    const regex = /^[a-zA-Z0-9]+#\d{4,5}$/;
    return regex.test(battleTag);
  };

  const checkMatch = async (silent = false) => {
    if (!playerData.nickname || !playerData.battle_tag || !playerData.race) {
      setError("Please fill in all fields");
      return;
    }

    if (!validateBattleTag(playerData.battle_tag)) {
      setError("Battle tag must be in format PlayerName#1234");
      return;
    }

    if (!silent) setLoading(true);
    setError("");
    
    try {
      const response = await axios.post(`${API}/check-match`, playerData);
      setMatchStatus(response.data);
      setLastChecked(new Date());
    } catch (err) {
      console.error("Error checking match:", err);
      setError(err.response?.data?.detail || "Failed to check match status");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const startAutoMonitoring = () => {
    if (!playerData.nickname || !playerData.battle_tag || !playerData.race) {
      setError("Please fill in all fields before starting auto-monitoring");
      return;
    }

    if (!validateBattleTag(playerData.battle_tag)) {
      setError("Battle tag must be in format PlayerName#1234");
      return;
    }

    setAutoMonitoring(true);
    
    // First check immediately
    checkMatch(true);
    
    // Then check every 5 seconds
    const id = setInterval(() => {
      checkMatch(true);
    }, 5000);
    
    setIntervalId(id);
  };

  const stopAutoMonitoring = () => {
    setAutoMonitoring(false);
    if (intervalId) {
      clearInterval(intervalId);
      setIntervalId(null);
    }
  };

  const showDemoMatch = async () => {
    console.log('Demo button clicked - fetching real data');
    setLoading(true);
    setError(""); // Clear any existing errors
    
    try {
      // FORCE React state update first
      const demoPlayerData = {
        nickname: "DemoPlayer", 
        battle_tag: "DemoPlayer#1234",
        race: "Human"
      };
      
      // Force state update and wait for it
      await new Promise((resolve) => {
        setPlayerData(demoPlayerData);
        setTimeout(resolve, 100); // Give React time to update
      });
      
      // FORCE DOM update as backup
      setTimeout(() => {
        if (nicknameRef.current) {
          nicknameRef.current.value = demoPlayerData.nickname;
          nicknameRef.current.dispatchEvent(new Event('input', { bubbles: true }));
        }
        if (battleTagRef.current) {
          battleTagRef.current.value = demoPlayerData.battle_tag;  
          battleTagRef.current.dispatchEvent(new Event('input', { bubbles: true }));
        }
        if (raceRef.current) {
          raceRef.current.value = demoPlayerData.race;
          raceRef.current.dispatchEvent(new Event('change', { bubbles: true }));
        }
      }, 150);
      
      // Fetch real demo match data from backend
      console.log('Fetching demo match data...');
      const response = await axios.get(`${API}/demo-match`);
      console.log('Demo match data received:', response.data);
      
      setMatchStatus(response.data);
      setLastChecked(new Date());
      
      console.log('Demo match setup complete');
      
    } catch (err) {
      console.error("Error fetching demo match:", err);
      setError(`Failed to load demo match data: ${err.message}`);
    } finally {
      setLoading(false);
    }
    
    // Static demo data removed - now using real backend data
  };

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [intervalId]);

  const getRaceIcon = (raceName) => {
    const race = races.find(r => r.value === raceName);
    return race?.icon || "❓";
  };

  const formatWinRate = (wins, losses) => {
    const total = wins + losses;
    if (total === 0) return "0%";
    return `${Math.round((wins / total) * 100)}%`;
  };

  const getHeroIcon = (heroId) => {
    const heroIcons = {
      "archmage": "🔮",
      "mountainking": "⚒️",
      "paladin": "🛡️",
      "bloodmage": "🩸",
      "blademaster": "⚔️",
      "farseer": "🌩️",
      "taurenchieftain": "🐂",
      "shadowhunter": "🏹",
      "demonhunter": "😈",
      "keeperofthegrove": "🌳",
      "moonpriestess": "🌙",
      "warden": "🦉",
      "deathknight": "💀",
      "dreadlord": "👹",
      "lich": "❄️",
      "cryptlord": "🕷️",
      "tinker": "⚙️",
      "bansheeranger": "⭐",
      "avatarofflame": "🔥"
    };
    return heroIcons[heroId] || "⭐";
  };

  // Map heroes to their races
  const getHeroesByRace = (race) => {
    const herosByRace = {
      "Human": ["archmage", "mountainking", "paladin", "bloodmage"],
      "Orc": ["blademaster", "farseer", "taurenchieftain", "shadowhunter"],
      "Night Elf": ["demonhunter", "keeperofthegrove", "moonpriestess", "warden", "bansheeranger"],
      "Undead": ["deathknight", "dreadlord", "lich", "cryptlord"],
      "Random": [] // Random can use any heroes
    };
    return herosByRace[race] || [];
  };

  const getPlayerRaceNumber = () => {
    const raceMap = {
      "Human": 1,
      "Orc": 2,
      "Night Elf": 4,
      "Undead": 8,
      "Random": 16
    };
    return raceMap[playerData.race] || 1;
  };

  const get_race_name_from_number = (raceNum) => {
    const raceMap = {
      0: "Random",
      1: "Human",
      2: "Orc",
      4: "Night Elf",
      8: "Undead",
      16: "Random"
    };
    return raceMap[raceNum] || "Unknown";
  };

  const OpponentCard = ({ opponent }) => {
    const playerRaceNum = getPlayerRaceNumber();
    
    // Calculate opponent's TOTAL winrate AGAINST my race from hero stats
    const getOpponentWinrateVsMyRace = () => {
      if (!opponent.hero_stats?.heroStatsItemList) return null;
      
      let totalWins = 0;
      let totalLosses = 0;
      
      // Sum up all hero stats against my race
      opponent.hero_stats.heroStatsItemList.forEach(heroStat => {
        heroStat.stats?.forEach(stat => {
          const overall = stat.winLossesOnMap?.find(wl => wl.map === "Overall");
          if (overall) {
            const vsMyRace = overall.winLosses?.find(wl => wl.race === playerRaceNum);
            if (vsMyRace && vsMyRace.games > 0) {
              totalWins += vsMyRace.wins;
              totalLosses += vsMyRace.losses;
            }
          }
        });
      });
      
      const totalGames = totalWins + totalLosses;
      if (totalGames === 0) return null;
      
      const winrate = Math.round((totalWins / totalGames) * 100);
      
      return {
        winrate,
        wins: totalWins,
        losses: totalLosses,
        games: totalGames
      };
    };

    const vsMyRaceStats = getOpponentWinrateVsMyRace();
    
    return (
      <Card className="bg-slate-800/50 border-amber-600/30" data-testid={`opponent-card-${opponent.battle_tag}`}>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-amber-400">
              <User className="w-5 h-5" />
              {opponent.battle_tag}
              <Badge variant="secondary" className="bg-amber-600/20 text-amber-300">
                {getRaceIcon(opponent.race)} {opponent.race}
              </Badge>
            </div>
            
            {/* MAIN FEATURE: Winrate vs My Race */}
            {vsMyRaceStats && (
              <div className="text-right">
                <div className={`text-2xl font-bold ${
                  vsMyRaceStats.winrate >= 65 ? 'text-red-400' : 
                  vsMyRaceStats.winrate >= 50 ? 'text-yellow-400' : 'text-green-400'
                }`}>
                  {vsMyRaceStats.winrate}%
                </div>
                <div className="text-xs text-slate-400">
                  vs {playerData.race}
                </div>
                <div className="text-xs text-slate-300">
                  {vsMyRaceStats.wins}W-{vsMyRaceStats.losses}L
                </div>
              </div>
            )}
          </CardTitle>
          
          {/* Highlight section for winrate vs my race */}
          {vsMyRaceStats && (
            <div className={`mt-3 p-3 rounded-lg border-2 ${
              vsMyRaceStats.winrate >= 65 ? 'bg-red-600/10 border-red-600/30' : 
              vsMyRaceStats.winrate >= 50 ? 'bg-yellow-600/10 border-yellow-600/30' : 'bg-green-600/10 border-green-600/30'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-lg">🎯</span>
                  <span className="font-semibold text-white">
                    {opponent.race} ПРОТИВ {playerData.race}
                  </span>
                </div>
                <div className="text-right">
                  <div className={`text-xl font-bold ${
                    vsMyRaceStats.winrate >= 65 ? 'text-red-300' : 
                    vsMyRaceStats.winrate >= 50 ? 'text-yellow-300' : 'text-green-300'
                  }`}>
                    {vsMyRaceStats.winrate}% против {playerData.race}
                  </div>
                  <div className="text-sm text-slate-300">
                    {vsMyRaceStats.games} матчей против вас, {vsMyRaceStats.wins}W-{vsMyRaceStats.losses}L
                  </div>
                </div>
              </div>
              
              <div className="mt-2 text-sm">
                {vsMyRaceStats.winrate >= 65 && (
                  <span className="text-red-300 font-semibold">🚨 КРИТИЧЕСКАЯ УГРОЗА! {vsMyRaceStats.winrate}% против {playerData.race} - будьте осторожны!</span>
                )}
                {vsMyRaceStats.winrate >= 50 && vsMyRaceStats.winrate < 65 && (
                  <span className="text-yellow-300 font-semibold">⚠️ СРЕДНЯЯ УГРОЗА! {vsMyRaceStats.winrate}% против {playerData.race} - стабильный противник</span>
                )}
                {vsMyRaceStats.winrate < 50 && (
                  <span className="text-green-300 font-semibold">✅ УЯЗВИМОСТЬ! Всего {vsMyRaceStats.winrate}% против {playerData.race} - используйте это!</span>
                )}
              </div>
            </div>
          )}
          
          {!vsMyRaceStats && (
            <div className="mt-3 p-3 rounded-lg bg-slate-700/30 border border-slate-600/30">
              <span className="text-slate-400 text-sm">
                📊 Нет данных против {playerData.race}
              </span>
            </div>
          )}
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Hero Statistics vs Your Race */}
          {opponent.hero_stats?.heroStatsItemList && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-purple-400">
                <Shield className="w-4 h-4" />
                <span className="text-sm font-semibold">Hero Picks vs {playerData.race}</span>
              </div>
              <div className="grid gap-2 max-h-64 overflow-y-auto">
                {opponent.hero_stats.heroStatsItemList.map((heroStat, idx) => {
                  // Find stats for this hero against your race
                  const heroVsYourRace = heroStat.stats.find(stat => 
                    stat.winLossesOnMap.some(mapStat => 
                      mapStat.winLosses.some(winLoss => winLoss.race === playerRaceNum && winLoss.games > 0)
                    )
                  );
                  
                  if (!heroVsYourRace) return null;
                  
                  const overallStats = heroVsYourRace.winLossesOnMap.find(map => map.map === "Overall");
                  const vsYourRaceStats = overallStats?.winLosses.find(wl => wl.race === playerRaceNum);
                  
                  if (!vsYourRaceStats || vsYourRaceStats.games === 0) return null;
                  
                  return (
                    <div key={idx} className="bg-slate-700/50 p-3 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{getHeroIcon(heroStat.heroId)}</span>
                          <span className="text-amber-300 font-medium capitalize">
                            {heroStat.heroId.replace(/([A-Z])/g, ' $1').trim()}
                          </span>
                        </div>
                        <div className="text-right">
                          <div className={`font-semibold ${vsYourRaceStats.winrate > 0.6 ? 'text-red-400' : 
                            vsYourRaceStats.winrate > 0.4 ? 'text-yellow-400' : 'text-green-400'}`}>
                            {Math.round(vsYourRaceStats.winrate * 100)}%
                          </div>
                          <div className="text-xs text-slate-400">
                            {vsYourRaceStats.wins}W-{vsYourRaceStats.losses}L
                          </div>
                        </div>
                      </div>
                      
                      {/* Map specific stats */}
                      <div className="space-y-1">
                        {heroVsYourRace.winLossesOnMap.filter(mapStat => 
                          mapStat.map !== "Overall" && 
                          mapStat.winLosses.some(wl => wl.race === playerRaceNum && wl.games > 0)
                        ).slice(0, 3).map((mapStat, mapIdx) => {
                          const mapVsYou = mapStat.winLosses.find(wl => wl.race === playerRaceNum);
                          if (!mapVsYou || mapVsYou.games === 0) return null;
                          
                          return (
                            <div key={mapIdx} className="text-xs flex justify-between text-slate-300">
                              <span className="truncate max-w-32">{mapStat.map.replace(/^\d+/, '').replace(/v\d+_\d+$/, '')}</span>
                              <span className={mapVsYou.winrate > 0.6 ? 'text-red-300' : 
                                mapVsYou.winrate > 0.4 ? 'text-yellow-300' : 'text-green-300'}>
                                {Math.round(mapVsYou.winrate * 100)}% ({mapVsYou.games})
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Overall Statistics */}
          {(opponent.basic_stats || opponent.race_stats) && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-green-400">
                  <Trophy className="w-4 h-4" />
                  <span className="text-sm">Race Statistics</span>
                </div>
                {opponent.basic_stats?.winLosses?.map((stat, idx) => (
                  <div key={idx} className="text-sm bg-slate-700/50 p-2 rounded">
                    <div className="flex justify-between">
                      <span>{getRaceIcon(get_race_name_from_number(stat.race))} {get_race_name_from_number(stat.race)}</span>
                      <span className="text-amber-300">{Math.round(stat.winrate * 100)}%</span>
                    </div>
                    <div className="text-xs text-slate-400">
                      {stat.wins}W - {stat.losses}L ({stat.games} games)
                    </div>
                  </div>
                )) || <div className="text-sm text-slate-400">No race statistics available</div>}
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-blue-400">
                  <Target className="w-4 h-4" />
                  <span className="text-sm">Recent Matches</span>
                </div>
                {opponent.recent_matches?.matches?.slice(0, 5).map((match, idx) => (
                  <div key={idx} className="text-xs bg-slate-700/50 p-2 rounded">
                    <div className="flex justify-between items-center">
                      <span className="text-amber-300 truncate">{match.map?.replace(/^\d+/, '') || "Unknown"}</span>
                      <Badge 
                        variant={match.won ? "success" : "destructive"}
                        className={match.won ? "bg-green-600/20 text-green-300" : "bg-red-600/20 text-red-300"}
                      >
                        {match.won ? "W" : "L"}
                      </Badge>
                    </div>
                    <div className="text-slate-400 mt-1">
                      {Math.round(match.durationInSeconds / 60)}m
                      {match.heroUsed && <span className="ml-2">{getHeroIcon(match.heroUsed.toLowerCase())}</span>}
                    </div>
                  </div>
                )) || <div className="text-sm text-slate-400">No recent matches found</div>}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl md:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-orange-500 mb-4">
            W3Champions Match Scout
          </h1>
          <p className="text-slate-300 text-lg max-w-2xl mx-auto">
            Monitor your Warcraft III matches and scout your opponents in real-time
          </p>
        </div>

        {/* Player Input Form */}
        <Card className="max-w-2xl mx-auto mb-8 bg-slate-800/50 border-amber-600/30" data-testid="player-input-form">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-400">
              <Shield className="w-5 h-5" />
              Player Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="nickname" className="text-slate-200">Nickname</Label>
                <Input
                  id="nickname"
                  ref={nicknameRef}
                  data-testid="nickname-input"
                  placeholder="Enter your nickname"
                  value={playerData.nickname}
                  onChange={(e) => handleInputChange("nickname", e.target.value)}
                  className="bg-slate-700 border-slate-600 text-white placeholder-slate-400"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="battle-tag" className="text-slate-200">Battle Tag</Label>
                <Input
                  id="battle-tag"
                  ref={battleTagRef}
                  data-testid="battle-tag-input"
                  placeholder="PlayerName#1234"
                  value={playerData.battle_tag}
                  onChange={(e) => handleInputChange("battle_tag", e.target.value)}
                  className="bg-slate-700 border-slate-600 text-white placeholder-slate-400"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-slate-200">Race</Label>
              <select
                ref={raceRef}
                data-testid="race-selector"
                value={playerData.race}
                onChange={(e) => handleInputChange("race", e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 text-white rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-600"
              >
                <option value="">Select your race</option>
                {races.map(race => (
                  <option key={race.value} value={race.value}>
                    {race.icon} {race.label}
                  </option>
                ))}
              </select>
            </div>

            {error && (
              <Alert className="border-red-600/50 bg-red-600/10">
                <AlertDescription className="text-red-400">{error}</AlertDescription>
              </Alert>
            )}

            <div className="grid md:grid-cols-2 gap-3">
              <Button
                onClick={() => checkMatch()}
                disabled={loading || autoMonitoring}
                className="bg-amber-600 hover:bg-amber-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                data-testid="check-match-btn"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Checking...
                  </>
                ) : (
                  <>
                    <Sword className="w-4 h-4 mr-2" />
                    Check Now
                  </>
                )}
              </Button>
              
              {!autoMonitoring ? (
                <Button
                  onClick={startAutoMonitoring}
                  disabled={loading}
                  className="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                  data-testid="start-monitoring-btn"
                >
                  <Target className="w-4 h-4 mr-2" />
                  Auto Monitor (5s)
                </Button>
              ) : (
                <Button
                  onClick={stopAutoMonitoring}
                  className="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                  data-testid="stop-monitoring-btn"
                >
                  <Clock className="w-4 h-4 mr-2" />
                  Stop Monitoring
                </Button>
              )}
            </div>

            {(lastChecked || autoMonitoring) && (
              <div className="flex items-center gap-4 text-sm justify-center">
                {lastChecked && (
                  <div className="flex items-center gap-2 text-slate-400">
                    <Clock className="w-4 h-4" />
                    Last checked: {lastChecked.toLocaleTimeString()}
                  </div>
                )}
                {autoMonitoring && (
                  <div className="flex items-center gap-2 text-green-400">
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                    Auto monitoring active
                  </div>
                )}
              </div>
            )}
            
            {/* Demo button */}
            <div className="text-center mt-4">
              <Button
                onClick={showDemoMatch}
                variant="outline"
                className="border-amber-600/50 text-amber-400 hover:bg-amber-600/10"
                data-testid="demo-match-btn"
              >
                <Trophy className="w-4 h-4 mr-2" />
                Show Demo Match Found
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Removed static test data */}

        {/* Match Status Results */}
        {matchStatus && (
          <div className="max-w-6xl mx-auto" data-testid="match-results">
            <Card className="mb-6 bg-slate-800/50 border-amber-600/30">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-amber-400">
                  <Target className="w-5 h-5" />
                  Match Status
                </CardTitle>
              </CardHeader>
              <CardContent>
                {matchStatus.status === "not_in_game" ? (
                  <Alert className="border-blue-600/50 bg-blue-600/10">
                    <AlertDescription className="text-blue-300">
                      Player {matchStatus.data.battle_tag} is not currently in a match.
                    </AlertDescription>
                  </Alert>
                ) : (
                  <Alert className="border-green-600/50 bg-green-600/10">
                    <AlertDescription className="text-green-300">
                      Match found! Player {matchStatus.data.battle_tag} is currently in game.
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            {/* Debug Match Status */}
            {matchStatus && (
              <Card className="mb-6 bg-slate-800/50 border-blue-600/30">
                <CardHeader>
                  <CardTitle className="text-blue-400">🔍 Debug: Match Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-sm text-slate-300 space-y-1">
                    <div>Status: {matchStatus.status}</div>
                    <div>Has data: {matchStatus.data ? 'Yes' : 'No'}</div>
                    <div>Has opponent_data: {matchStatus.data?.opponent_data ? 'Yes' : 'No'}</div>
                    <div>Has opponents: {matchStatus.data?.opponent_data?.opponents ? 'Yes' : 'No'}</div>
                    <div>Opponents count: {matchStatus.data?.opponent_data?.opponents?.length || 0}</div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Opponent Information */}
            {matchStatus && matchStatus.status === "in_game" && matchStatus.data && matchStatus.data.opponent_data && matchStatus.data.opponent_data.opponents && matchStatus.data.opponent_data.opponents.length > 0 && (
              <div className="space-y-6">
                <div className="text-center">
                  <h2 className="text-2xl font-bold text-amber-400 mb-2">🎯 Анализ Противника - ПРОТИВ {playerData.race}</h2>
                  <Separator className="bg-amber-600/30" />
                </div>
                <div className="grid gap-6">
                  {matchStatus.data.opponent_data.opponents.map((opponent, index) => (
                    <OpponentCard key={index} opponent={opponent} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;