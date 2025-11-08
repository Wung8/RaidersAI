# game_server.py
import socket
import threading
import pickle
import struct
import sys
import pygame
import time
import traceback

import raiders
import env_utils
from env_utils import RaiderEnvironmentWrapper


MSG_LEN_STRUCT = struct.Struct("!I")  # 4-byte unsigned int length prefix


def send_msg(conn, obj):
    """Send a length-prefixed pickled object."""
    data = pickle.dumps(obj)
    conn.sendall(MSG_LEN_STRUCT.pack(len(data)) + data)


def recv_msg(conn):
    """Receive a single length-prefixed pickled object. Returns None on error/closed."""
    try:
        header = conn.recv(MSG_LEN_STRUCT.size)
        if not header:
            return None
        (length,) = MSG_LEN_STRUCT.unpack(header)
        data = b""
        while len(data) < length:
            packet = conn.recv(length - len(data))
            if not packet:
                return None
            data += packet
        return pickle.loads(data)
    except Exception:
        return None


class GameServer:
    def __init__(self, host='0.0.0.0', port=12345):
        pygame.init()
        self.host = host
        self.port = port

        # create environment wrapper in "god" mode as requested
        self.env = RaiderEnvironmentWrapper(mode="god")

        # network
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(1.0)
        self.sock.bind((host, port))
        self.sock.listen()

        # bookkeeping
        self.pending_new_players = []
        self.pending_remove_players = []
        self.clients = {}  # conn -> {'player_id': int, 'thread': Thread}
        self.player_conn = {}  # player_id -> conn
        self.running = True
        self.lock = threading.Lock()  # protects clients/player_conn
        self.env_lock = threading.Lock()

    def accept_loop(self):
        print(f"[server] listening on {self.host}:{self.port}")
        while self.running:
            try:
                conn, addr = self.sock.accept()
                print(f"[server] connection from {addr}")
                # For registration: expect a register message first
                reg = recv_msg(conn)
                if not reg or not isinstance(reg, dict) or reg.get("type") != "register":
                    print("[server] invalid or no registration; closing connection")
                    conn.close()
                    continue
                team = reg.get("team")

                with self.lock:
                    self.pending_new_players.append((conn, team))
                print(f"[server] queued player for team '{team}'")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[server] accept error: {e}")
                continue

    def client_recv_loop(self, conn):
        """Receive messages (actions) from a client and update env.actions accordingly."""
        try:
            while self.running:
                msg = recv_msg(conn)
                if msg is None:
                    break
                # Expect messages of form {'type': 'action', 'player_id': int, 'action': [...]}
                if not isinstance(msg, dict):
                    continue
                if msg.get('type') == 'action':
                    player_id = msg.get('player_id')
                    action = msg.get('action')
                    if player_id is None or action is None:
                        continue
                    action = action[:-1] + (env_utils.convAngleToAction(self.env.env.players[player_id].angle, action[-1]),)
                    # validate range
                    with self.lock:
                        if player_id in self.env.actions:
                            self.env.actions[player_id] = action
                        else:
                            print("player id not found")
                    
                    if "name" in msg:
                        self.env.env.players[player_id].name = msg["name"]
                # ignore other message types
        except Exception as e:
            print(f"[server] client_recv_loop error: {e}")
        finally:
            # cleanup connection
            with self.lock:
                info = self.clients.pop(conn, None)
                if info:
                    pid = info.get('player_id')
                    self.player_conn.pop(pid, None)
            try:
                conn.close()
            except:
                pass
            print("[server] client disconnected")
            self.pending_remove_players.append(pid)
            

    def process_object(self, obj):
        '''
        type, x, y, health, angle, hit, r, g, b
        '''
        info = (0, 0, 0, 0, 0, 0, 0, 0, 0)
        match type(obj):
            case raiders.Player:
                info = (-1, obj.pos[0], obj.pos[1], obj.health, obj.angle, obj.hit, *obj.color, obj.active, obj.attack_tick, obj.frames, obj.id_, obj.kills)
            case raiders.Heal:
                info = (0, obj.pos[0], obj.pos[1], 0, 0, 0, 0, 0, 0)
            case raiders.Arrow:
                info = (1, obj.pos[0], obj.pos[1], 0, obj.angle, 0, 0, 0, 0)
            case raiders.ChargedArrow:
                info = (2, obj.pos[0], obj.pos[1], 0, obj.angle, 0, 0, 0, 0)
            case raiders.Bullet:
                info = (3, obj.pos[0], obj.pos[1], 0, 0, 0, 0, 0, 0)
            case raiders.Frag:
                info = (4, obj.pos[0], obj.pos[1], 0, 0, 0, 0, 0, 0)
            case raiders.Explosion:
                info = (5, obj.pos[0], obj.pos[1], 0, 0, 0, 0, 0, 0)
            case raiders.Turret:
                info = (6, obj.pos[0], obj.pos[1], 0, obj.angle, obj.hit, *obj.color)
            case raiders.Bush:
                info = (7, obj.pos[0], obj.pos[1], obj.health, 0, obj.hit, 0, 0, 0)
            case raiders.Tree:
                info = (8, obj.pos[0], obj.pos[1], obj.health, 0, obj.hit, 0, 0, 0)
            case raiders.Stone:
                info = (9, obj.pos[0], obj.pos[1], obj.health, 0, obj.hit, 0, 0, 0)
            case raiders.WoodWall:
                info = (10, obj.pos[0], obj.pos[1], 0, 0, obj.hit, 0, 0, 0)
            case raiders.StoneWall:
                info = (11, obj.pos[0], obj.pos[1], 0, 0, obj.hit, *obj.color)
            case raiders.Spike:
                info = (12, obj.pos[0], obj.pos[1], -1, 0, obj.hit, *obj.color)
            case raiders.Base:
                info = (13, obj.pos[0], obj.pos[1], obj.health, 0, obj.hit, 0, 0, 0)
            
        
        return info

    def broadcast_frame(self, frame_surf):
        """Encode a pygame Surface as raw RGB and broadcast to all clients as a frame message."""
        # Convert surface to RGB raw bytes
        try:
            # ensure the frame is the surface the env used for display (screen)
            w, h = frame_surf.get_size()

            objects = [self.env.env.base]
            for obj in self.env.env.effects:
                objects.append(obj)
            for obj in self.env.env.objects:
                if isinstance(obj, raiders.Tree):
                    continue
                objects.append(obj)
            for obj in self.env.env.dynamic_objects:
                if isinstance(obj, raiders.Player) or isinstance(obj, raiders.Base):
                    continue
                objects.append(obj)
            for obj in self.env.env.getPlayers():
                #if obj.health <= 0: 
                #    continue
                objects.append(obj)
            for obj in self.env.env.objects:
                if not isinstance(obj, raiders.Tree):
                    continue
                objects.append(obj)
            
            for i in range(len(objects)):
                objects[i] = self.process_object(objects[i])

            msg = {
                'type': 'frame',
                #'img_bytes': img_bytes,
                'map_size': self.env.env.map_size,
                'size': (w, h),
                'timestamp': time.time(),
                'ids': self.env.getActiveIDs(),
                'teams': self.env.env.getTeamCounts(),
                'info': {
                    'names': {id_:obs.self.name for id_, obs in self.observations.items()},
                    'healths': {id_:obs.self.health for id_, obs in self.observations.items()},
                    'angles': {id_:obs.self.angle for id_, obs in self.observations.items()},
                    'positions': {id_:obs.self.position for id_, obs in self.observations.items()},
                    'food': {id_:obs.self.food for id_, obs in self.observations.items()},
                    'wood': {id_:obs.self.wood for id_, obs in self.observations.items()},
                    'stone': {id_:obs.self.stone for id_, obs in self.observations.items()},
                    'objects': objects,
                    'sounds': self.env.env.sounds,
                    'stormsize': self.env.env.storm_size,
                }
            }

            with self.lock:
                conns = list(self.clients.keys())

            for conn in conns:
                try:
                    send_msg(conn, msg)
                except Exception:
                    # client may have dropped; client_recv_loop will clean up
                    pass
        except Exception as e:
            print(f"[server] frame broadcast error: {e}")
            traceback.print_exc()

    def game_loop(self):
        """Main game loop: step the environment, display (which updates env.screen), broadcast the frame, handle quit."""
        print("[server] entering game loop")
        try:
            buffer = 5*20
            done = False
            while self.running:
                # Use env.step(display=True) so the env wrapper updates the display surfaces and handles camera controls
                keys = pygame.key.get_pressed()
                if keys[pygame.K_r]:
                    self.env.reset()
                    buffer = 5*20
                    done = False
                
                if keys[pygame.K_u]:
                    if not any(isinstance(script, env_utils.AgentScripts.BasicAgent) and script.__team__=="defender" for script in self.env.scripts):
                        self.env.addScript(env_utils.AgentScripts.BasicAgent)
                    for script in self.env.scripts:
                        if isinstance(script, env_utils.AgentScripts.BasicAgent) and script.__team__=="defender":
                            print(type(script))
                            self.env.removeAgent(script=script)
                            break
                if keys[pygame.K_i]:
                    if not any(isinstance(script, env_utils.AgentScripts.BasicAgent) and script.__team__=="raider" for script in self.env.scripts):
                        self.env.addScript(env_utils.AgentScripts.BasicAgent)
                    for script in self.env.scripts:
                        if isinstance(script, env_utils.AgentScripts.BasicAgent) and script.__team__=="raider":
                            print(type(script))
                            self.env.removeAgent(script=script)
                            break
                if keys[pygame.K_o]:
                    if not any(isinstance(script, env_utils.AgentScripts.BasicAgent) and script.__team__=="defender" for script in self.env.scripts):
                        self.env.addScript(env_utils.AgentScripts.BasicAgent)
                    for script in self.env.scripts:
                        if isinstance(script, env_utils.AgentScripts.BasicAgent) and script.__team__=="defender":
                            print(type(script))
                            self.env.addAgent(script=script)
                            break
                if keys[pygame.K_p]:
                    if not any(isinstance(script, env_utils.AgentScripts.BasicAgent) and script.__team__=="raider" for script in self.env.scripts):
                        self.env.addScript(env_utils.AgentScripts.BasicAgent)
                    for script in self.env.scripts:
                        if isinstance(script, env_utils.AgentScripts.BasicAgent) and script.__team__=="raider":
                            print(type(script))
                            self.env.addAgent(script=script)
                            break


                # Handle new player joins safely
                with self.lock:
                    while self.pending_new_players:
                        conn, team = self.pending_new_players.pop(0)
                        with self.env_lock:
                            player_id = self.env.addAgent(team=team)
                        print(f"[server] created player {player_id} for team '{team}'")
                        send_msg(conn, {"type": "register_ack", "player_id": player_id, "team": team})

                        # set up connection bookkeeping
                        self.clients[conn] = {'player_id': player_id, 'addr': conn.getpeername(), 'team': team}
                        self.player_conn[player_id] = conn
                        t = threading.Thread(target=self.client_recv_loop, args=(conn,), daemon=True)
                        t.start()
                        self.clients[conn]['thread'] = t
                    while self.pending_remove_players:
                        pid = self.pending_remove_players.pop()
                        with self.env_lock:
                            self.env.removeAgent(pid)
                            print(f"[server] removed player {pid}")

                observations, rewards, terminated, truncated, info = self.env.step(display=True)
                self.observations = observations

                # grab the screen buffer from the environment's screen surface
                frame = self.env.env.surface

                # broadcast the frame to all clients
                self.broadcast_frame(frame)

                # handle pygame events (quit)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        print("[server] pygame QUIT received")
                        self.running = False

                if terminated:
                    done = True

                if done:
                    buffer -= 1
                
                if buffer == 0:
                    self.env.reset()
                    buffer = 5*20
                    done = False

        except KeyboardInterrupt:
            print("[server] KeyboardInterrupt")
            self.running = False
        finally:
            self.shutdown()

    def shutdown(self):
        print("[server] shutting down")
        self.running = False
        with self.lock:
            conns = list(self.clients.keys())
        for conn in conns:
            try:
                send_msg(conn, {'type': 'server_shutdown'})
            except:
                pass
            try:
                conn.shutdown(socket.SHUT_RDWR)
                conn.close()
            except:
                pass
        try:
            self.sock.close()
        except:
            pass
        try:
            pygame.quit()
        except:
            pass
        print("[server] stopped")


if __name__ == "__main__":
    # If you want to include agents/scripts, construct them and pass into GameServer(..., agent_scripts=[...])
    # For now, we pass an empty agent_scripts list so server still runs and uses only player actions and default agents.
    myip = "127.0.0.1"
    agent_scripts = [
        (env_utils.AgentScripts.MatthewAgent(), 5, "defender"),
        (env_utils.AgentScripts.BasicAgent(), 10, "raider")
    ]
    server = GameServer(host=myip, port=9999)
    server.env.loadAgentScripts(agent_scripts)
    server.env.reset()
    accept_thread = threading.Thread(target=server.accept_loop, daemon=True)
    accept_thread.start()
    server.game_loop()
