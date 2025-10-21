import json
from ryu.app.wsgi import ControllerBase, route
from webob import Response

api_instance_name = "ryu_controller_api"

def cors_response(body: str, status: int = 200):
    """
    Helper function to create a JSON Response with CORS headers.
    """
    return Response(
        content_type='application/json',
        body=body.encode('utf-8'),
        status=status,
        headers={
            'Access-Control-Allow-Origin': '*',  # allow all origins (dev only)
            'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
    )

class RyuControllerApi(ControllerBase):
    """
    REST API kontroler za SDN aplikaciju.
    Pruža endpointe za pristup stanju kontrolera.
    """

    def __init__(self, req, link, data, **config):
        super(RyuControllerApi, self).__init__(req, link, data, **config)
        self.controller = data[api_instance_name]

    @route('whitelist', '/whitelist', methods=['GET'])
    def get_whitelist(self, req, **kwargs):
        app = self.controller
        whitelist = [{'src': src, 'dst': dst} for src, dst in app.ALLOWED_PAIRS]
        body = json.dumps({'whitelist': whitelist})
        return cors_response(body)

    @route('topology', '/topology', methods=['GET'])
    def get_topology(self, req, **kwargs):
        app = self.controller
        
        # Formatiraj host_info u čitljiv format
        hosts = []
        for ip, (mac, switch_id, port) in app.host_info.items():
            hosts.append({
                'ip': ip,
                'mac': mac,
                'switch': switch_id,
                'port': port
            })
        
        # Formatiraj mac_to_port (switchevi i njihovi portovi)
        switches = []
        for switch_id, mac_ports in app.mac_to_port.items():
            ports = [{'mac': mac, 'port': port} for mac, port in mac_ports.items()]
            switches.append({
                'switch_id': switch_id,
                'ports': ports
            })
        
        topology = {
            'hosts': hosts,
            'switches': switches
        }
        
        body = json.dumps(topology, indent=2)
        return cors_response(body)
    
    @route('whitelist', '/whitelist', methods=['POST'])
    def add_to_whitelist(self, req, **kwargs):
        app = self.controller
        try:
            data = json.loads(req.body)
            src_ip = data['src']
            dst_ip = data['dst']
            
            app.ALLOWED_PAIRS.add((src_ip, dst_ip))
            app.logger.info(f"Dodan whitelist par: {src_ip} -> {dst_ip}")
            
            return cors_response(body=json.dumps({
                'status': 'success',
                'message': f'Added {src_ip} -> {dst_ip}'
            }))
        except Exception as e:
            return cors_response(body=json.dumps({
                'status': 'error',
                'message': str(e)
            }), status=400)
        
    @route('whitelist', '/whitelist', methods=['DELETE'])
    def remove_from_whitelist(self, req, **kwargs):
        app = self.controller
        try:
            data = json.loads(req.body)
            src_ip = data['src']
            dst_ip = data['dst']
            
            app.ALLOWED_PAIRS.discard((src_ip, dst_ip))
            app.logger.info(f"Obrisan whitelist par: {src_ip} -> {dst_ip}")
            
            return cors_response(body=json.dumps({
                'status': 'success',
                'message': f'Removed {src_ip} -> {dst_ip}'
            }))
        except Exception as e:
            return cors_response(body=json.dumps({
                'status': 'error',
                'message': str(e)
            }), status=400)
    
    @route('stats', '/stats', methods=['GET'])
    def get_stats(self, req, **kwargs):
        app = self.controller
        stats = {
            'total_hosts': len(app.host_info),
            'total_switches': len(app.mac_to_port),
            'whitelist_rules': len(app.ALLOWED_PAIRS)
        }
        body = json.dumps(stats)
        return cors_response(body)
    
    @route('whitelist', '/whitelist', methods=['OPTIONS'])
    def options_whitelist(self, req, **kwargs):
        return cors_response('{}')