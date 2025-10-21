import { useState, useEffect } from 'react';
import {
  MantineProvider,
  AppShell,
  Container,
  Title,
  Tabs,
  Card,
  Text,
  Group,
  Stack,
  Button,
  TextInput,
  Table,
  Badge,
  Alert,
  Loader,
  Grid,
} from '@mantine/core';
import {
  IconNetwork,
  IconList,
  IconChartBar,
  IconPlus,
  IconTrash,
  IconAlertCircle,
} from '@tabler/icons-react';

// ===== Types =====
interface WhitelistRule {
  src: string;
  dst: string;
}

interface Host {
  ip: string;
  mac: string;
  switch: string;
  port: number;
}

interface SwitchPort {
  port: number;
  mac: string;
}

interface Switch {
  switch_id: string;
  ports: SwitchPort[];
}

interface Topology {
  hosts: Host[];
  switches: Switch[];
}

interface Stats {
  total_hosts: number;
  total_switches: number;
  whitelist_rules: number;
}

interface ApiResponse<T> {
  status?: string;
  message?: string;
  whitelist?: WhitelistRule[];
  data?: T;
}

function App() {
  const apiUrl = 'http://localhost:8080';
  const [whitelist, setWhitelist] = useState<WhitelistRule[]>([]);
  const [topology, setTopology] = useState<Topology>({ hosts: [], switches: [] });
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newSrc, setNewSrc] = useState('');
  const [newDst, setNewDst] = useState('');

  const fetchWhitelist = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${apiUrl}/whitelist`);
      const data: ApiResponse<WhitelistRule[]> = await res.json();
      setWhitelist(data.whitelist || []);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Failed to fetch whitelist: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchTopology = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${apiUrl}/topology`);
      const data: Topology = await res.json();
      setTopology(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Failed to fetch topology: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${apiUrl}/stats`);
      const data: Stats = await res.json();
      setStats(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Failed to fetch stats: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const addWhitelistRule = async () => {
    if (!newSrc || !newDst) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${apiUrl}/whitelist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ src: newSrc, dst: newDst }),
      });
      const data: ApiResponse<null> = await res.json();
      if (data.status === 'success') {
        setNewSrc('');
        setNewDst('');
        await fetchWhitelist();
      } else {
        setError(data.message || 'Failed to add rule');
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Failed to add rule: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const removeWhitelistRule = async (src: string, dst: string) => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${apiUrl}/whitelist`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ src, dst }),
      });
      const data: ApiResponse<null> = await res.json();
      if (data.status === 'success') {
        await fetchWhitelist();
      } else {
        setError(data.message || 'Failed to remove rule');
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Failed to remove rule: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchWhitelist();
    void fetchTopology();
    void fetchStats();
  }, []);

  return (
    <MantineProvider theme={{ primaryColor: 'blue' }}>
      <AppShell padding="md">
        <Container size="xl">
          <Stack gap="lg">
            <Title order={1}>Ryu SDN Controller Dashboard</Title>

            {error && (
              <Alert
                icon={<IconAlertCircle size={16} />}
                color="red"
                onClose={() => setError(null)}
                withCloseButton
              >
                {error}
              </Alert>
            )}

            <Tabs defaultValue="whitelist">
              <Tabs.List>
                <Tabs.Tab value="whitelist" leftSection={<IconList size={16} />}>
                  Whitelist
                </Tabs.Tab>
                <Tabs.Tab value="topology" leftSection={<IconNetwork size={16} />}>
                  Topology
                </Tabs.Tab>
                <Tabs.Tab value="stats" leftSection={<IconChartBar size={16} />}>
                  Statistics
                </Tabs.Tab>
              </Tabs.List>

              {/* Whitelist Panel */}
              <Tabs.Panel value="whitelist" pt="md">
                <Stack gap="md">
                  <Card shadow="sm" padding="lg">
                    <Stack gap="md">
                      <Title order={3}>Add Whitelist Rule</Title>
                      <Group grow>
                        <TextInput
                          label="Source IP"
                          placeholder="10.0.0.1"
                          value={newSrc}
                          onChange={(e) => setNewSrc(e.target.value)}
                        />
                        <TextInput
                          label="Destination IP"
                          placeholder="10.0.0.2"
                          value={newDst}
                          onChange={(e) => setNewDst(e.target.value)}
                        />
                      </Group>
                      <Button
                        leftSection={<IconPlus size={16} />}
                        onClick={addWhitelistRule}
                        loading={loading}
                      >
                        Add Rule
                      </Button>
                    </Stack>
                  </Card>

                  <Card shadow="sm" padding="lg">
                    <Group justify="space-between" mb="md">
                      <Title order={3}>Current Rules</Title>
                      <Button onClick={fetchWhitelist} loading={loading}>
                        Refresh
                      </Button>
                    </Group>

                    {loading && <Loader />}
                    {!loading && whitelist.length === 0 && (
                      <Text c="dimmed">No whitelist rules configured</Text>
                    )}
                    {!loading && whitelist.length > 0 && (
                      <Table>
                        <Table.Thead>
                          <Table.Tr>
                            <Table.Th>Source IP</Table.Th>
                            <Table.Th>Destination IP</Table.Th>
                            <Table.Th>Action</Table.Th>
                          </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                          {whitelist.map((rule, idx) => (
                            <Table.Tr key={idx}>
                              <Table.Td>
                                <Badge color="blue">{rule.src}</Badge>
                              </Table.Td>
                              <Table.Td>
                                <Badge color="green">{rule.dst}</Badge>
                              </Table.Td>
                              <Table.Td>
                                <Button
                                  size="xs"
                                  color="red"
                                  leftSection={<IconTrash size={14} />}
                                  onClick={() => removeWhitelistRule(rule.src, rule.dst)}
                                >
                                  Remove
                                </Button>
                              </Table.Td>
                            </Table.Tr>
                          ))}
                        </Table.Tbody>
                      </Table>
                    )}
                  </Card>
                </Stack>
              </Tabs.Panel>

              {/* Topology Panel */}
              <Tabs.Panel value="topology" pt="md">
                <Stack gap="md">
                  <Group justify="flex-end">
                    <Button onClick={fetchTopology} loading={loading}>
                      Refresh
                    </Button>
                  </Group>

                  <Grid>
                    {/* Hosts */}
                    <Grid.Col span={6}>
                      <Card shadow="sm" padding="lg">
                        <Title order={3} mb="md">
                          Hosts
                        </Title>
                        {loading && <Loader />}
                        {!loading && topology.hosts.length === 0 && (
                          <Text c="dimmed">No hosts detected</Text>
                        )}
                        {!loading && topology.hosts.length > 0 && (
                          <Table>
                            <Table.Thead>
                              <Table.Tr>
                                <Table.Th>IP</Table.Th>
                                <Table.Th>MAC</Table.Th>
                                <Table.Th>Switch</Table.Th>
                                <Table.Th>Port</Table.Th>
                              </Table.Tr>
                            </Table.Thead>
                            <Table.Tbody>
                              {topology.hosts.map((host, idx) => (
                                <Table.Tr key={idx}>
                                  <Table.Td>
                                    <Badge>{host.ip}</Badge>
                                  </Table.Td>
                                  <Table.Td>
                                    <Text size="sm">{host.mac}</Text>
                                  </Table.Td>
                                  <Table.Td>
                                    <Badge color="cyan">{host.switch}</Badge>
                                  </Table.Td>
                                  <Table.Td>{host.port}</Table.Td>
                                </Table.Tr>
                              ))}
                            </Table.Tbody>
                          </Table>
                        )}
                      </Card>
                    </Grid.Col>

                    {/* Switches */}
                    <Grid.Col span={6}>
                      <Card shadow="sm" padding="lg">
                        <Title order={3} mb="md">
                          Switches
                        </Title>
                        {loading && <Loader />}
                        {!loading && topology.switches.length === 0 && (
                          <Text c="dimmed">No switches detected</Text>
                        )}
                        {!loading && topology.switches.length > 0 && (
                          <Stack gap="md">
                            {topology.switches.map((sw, idx) => (
                              <Card key={idx} withBorder>
                                <Title order={5} mb="xs">
                                  Switch {sw.switch_id}
                                </Title>
                                <Text size="sm" c="dimmed" mb="xs">
                                  {sw.ports.length} port(s)
                                </Text>
                                {sw.ports.slice(0, 5).map((port, pidx) => (
                                  <Text key={pidx} size="xs">
                                    Port {port.port}: {port.mac}
                                  </Text>
                                ))}
                                {sw.ports.length > 5 && (
                                  <Text size="xs" c="dimmed">
                                    ... and {sw.ports.length - 5} more
                                  </Text>
                                )}
                              </Card>
                            ))}
                          </Stack>
                        )}
                      </Card>
                    </Grid.Col>
                  </Grid>
                </Stack>
              </Tabs.Panel>

              {/* Stats Panel */}
              <Tabs.Panel value="stats" pt="md">
                <Stack gap="md">
                  <Group justify="flex-end">
                    <Button onClick={fetchStats} loading={loading}>
                      Refresh
                    </Button>
                  </Group>

                  {loading && <Loader />}
                  {!loading && stats && (
                    <Grid>
                      <Grid.Col span={4}>
                        <Card shadow="sm" padding="lg" withBorder>
                          <Stack gap="xs" align="center">
                            <Text size="xl" fw={700}>
                              {stats.total_hosts}
                            </Text>
                            <Text c="dimmed">Total Hosts</Text>
                          </Stack>
                        </Card>
                      </Grid.Col>
                      <Grid.Col span={4}>
                        <Card shadow="sm" padding="lg" withBorder>
                          <Stack gap="xs" align="center">
                            <Text size="xl" fw={700}>
                              {stats.total_switches}
                            </Text>
                            <Text c="dimmed">Total Switches</Text>
                          </Stack>
                        </Card>
                      </Grid.Col>
                      <Grid.Col span={4}>
                        <Card shadow="sm" padding="lg" withBorder>
                          <Stack gap="xs" align="center">
                            <Text size="xl" fw={700}>
                              {stats.whitelist_rules}
                            </Text>
                            <Text c="dimmed">Whitelist Rules</Text>
                          </Stack>
                        </Card>
                      </Grid.Col>
                    </Grid>
                  )}
                </Stack>
              </Tabs.Panel>
            </Tabs>
          </Stack>
        </Container>
      </AppShell>
    </MantineProvider>
  );
}

export default App;
