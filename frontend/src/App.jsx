import { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Box,
  Button,
  Group,
  MultiSelect,
  NumberInput,
  TextInput,
  Title,
  Text,
  Stack,
  Card,
  ActionIcon,
  Modal,
  Select,
  Table,
  SegmentedControl,
  Container,
  Paper,
  Transition,
  Divider,
  Badge,
  Collapse,
  Menu,
  Textarea,
  Alert
} from '@mantine/core';
import { TimeInput } from '@mantine/dates';
import { IconTrash, IconDownload, IconClock, IconPlus, IconFilter, IconMessageCircle, IconInfoCircle } from '@tabler/icons-react';
import { ChatWindow } from './components/ChatWindow';

function App() {
  const [columns, setColumns] = useState([]);
  const [segments, setSegments] = useState([]);
  const [conditions, setConditions] = useState({});
  const [segmentName, setSegmentName] = useState('');
  const [stats, setStats] = useState(null);
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [selectedSegment, setSelectedSegment] = useState(null);
  const [scheduleInterval, setScheduleInterval] = useState('24');
  const [exportFormat, setExportFormat] = useState('csv');
  const [exportDestination, setExportDestination] = useState('none');
  const [schedules, setSchedules] = useState([]);
  const [scheduleType, setScheduleType] = useState('interval');
  const [scheduleTime, setScheduleTime] = useState('12:00');
  const [showMetadata, setShowMetadata] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [showSqlEditor, setShowSqlEditor] = useState(false);
  const [sqlQuery, setSqlQuery] = useState('');
  const [sqlSegmentName, setSqlSegmentName] = useState('');
  const [sqlStats, setSqlStats] = useState(null);
  const [activeSegmentType, setActiveSegmentType] = useState(null);

  useEffect(() => {
    loadColumns();
    loadSegments();
    loadSchedules();
  }, []);

  useEffect(() => {
    if (Object.keys(conditions).length > 0) {
      evaluateSegment();
    } else {
      setStats(null);
    }
  }, [conditions]);

  const loadColumns = async () => {
    const response = await axios.get('/api/columns');
    const metadata = {
      'CustomerID': { type: 'String', description: 'Unique identifier assigned to each customer (e.g. "C001")' },
      'Name': { type: 'String', description: 'Full name of the customer' },
      'Age': { type: 'Integer', description: 'Age of the customer in years' },
      'Gender': { type: 'String', description: 'Gender identity of the customer ("Male", "Female", "Non-Binary")' },
      'Location': { type: 'String', description: "Customer's primary city of residence" },
      'AccountType': { type: 'String', description: 'Type of bank account held ("Checking" or "Savings")' },
      'Balance': { type: 'Float', description: 'Current available balance in the account, in USD' },
      'AccountOpenDate': { type: 'Date', description: 'Date the customer opened the account' },
      'TxnCount_1M': { type: 'Integer', description: 'Number of transactions made in the last 1 month' },
      'TxnCount_3M': { type: 'Integer', description: 'Number of transactions made in the last 3 months' },
      'TxnCount_12M': { type: 'Integer', description: 'Number of transactions made in the last 12 months' },
      'AvgTxnAmt_1M': { type: 'Float', description: 'Average dollar amount per transaction over the last 1 month' },
      'AvgTxnAmt_3M': { type: 'Float', description: 'Average dollar amount per transaction over the last 3 months' },
      'AvgTxnAmt_12M': { type: 'Float', description: 'Average dollar amount per transaction over the last 12 months' },
      'TotalDeposits_3M': { type: 'Float', description: 'Total value of deposits made in the last 3 months, in USD' },
      'TotalWithdrawals_3M': { type: 'Float', description: 'Total value of withdrawals made in the last 3 months, in USD' }
    };

    const columnsWithMetadata = response.data.columns.map(col => ({
      ...col,
      type: metadata[col.name]?.type || col.type,
      description: metadata[col.name]?.description || ''
    }));

    setColumns(columnsWithMetadata);
  };

  const loadSegments = async () => {
    const response = await axios.get('/api/segments');
    setSegments(response.data);
  };

  const loadSchedules = async () => {
    const response = await axios.get('/api/schedules');
    setSchedules(response.data);
  };

  const evaluateSegment = async () => {
    const response = await axios.post('/api/evaluate-segment', conditions);
    setStats(response.data);
  };

  const evaluateSqlSegment = async () => {
    try {
      const response = await axios.post('/api/evaluate-sql-segment', {
        query: sqlQuery
      });
      setSqlStats(response.data);
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: error.response?.data?.detail || 'Failed to evaluate SQL query',
        color: 'red'
      });
    }
  };

  const handleSaveSegment = async () => {
    if (!segmentName) return;
    await axios.post('/api/save-segment', {
      name: segmentName,
      conditions
    });
    loadSegments();
    setSegmentName('');
  };

  const handleSaveSqlSegment = async () => {
    if (!sqlSegmentName || !sqlQuery) return;
    try {
      await axios.post('/api/save-sql-segment', {
        name: sqlSegmentName,
        query: sqlQuery
      });
      loadSegments();
      setSqlSegmentName('');
      setSqlQuery('');
      setShowSqlEditor(false);
      notifications.show({
        title: 'Success',
        message: 'SQL segment saved successfully',
        color: 'green'
      });
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: error.response?.data?.detail || 'Failed to save SQL segment',
        color: 'red'
      });
    }
  };

  const handleExportNow = async (segmentName) => {
    await axios.post('/api/export-now', {
      segment_name: segmentName,
      format: exportFormat,
      destination: exportDestination
    });
  };

  const handleScheduleExport = async () => {
    if (!selectedSegment) return;

    const scheduleData = {
      segment_name: selectedSegment,
      format: exportFormat,
      destination: exportDestination,
    };

    if (scheduleType === 'interval') {
      scheduleData.interval_hours = parseInt(scheduleInterval);
    } else {
      scheduleData.run_time = scheduleTime;
    }

    await axios.post('/api/schedule-export', scheduleData);
    loadSchedules();
    setScheduleModalOpen(false);
  };

  const addCondition = (column) => {
    const columnData = columns.find(c => c.name === column);
    if (columnData.type === 'Integer' || columnData.type === 'Float') {
      setConditions(prev => ({
        ...prev,
        [column]: { min: null, max: null }
      }));
    } else {
      setConditions(prev => ({
        ...prev,
        [column]: { values: [] }
      }));
    }
  };

  const updateCondition = (column, type, value) => {
    setConditions(prev => ({
      ...prev,
      [column]: {
        ...prev[column],
        [type]: value
      }
    }));
  };

  const deleteCondition = (column) => {
    setConditions(prev => {
      const newConditions = { ...prev };
      delete newConditions[column];
      return newConditions;
    });
  };

  const deleteSegment = async (segmentName) => {
    await axios.delete(`/api/segments/${segmentName}`);
    loadSegments();
  };

  const [userInfo, setUserInfo] = useState({ name: 'Unknown', email: 'Unknown' });

  useEffect(() => {
    fetch('/api/user')
      .then(response => response.json())
      .then(data => setUserInfo(data));
  }, []);

  return (
    <Container size="xl">
      <Group position="apart" mb="xl">
        <div>
          <Title order={1} mb="xs">Customer Segmentation</Title>
          <Text color="dimmed">Create and manage your customer segments</Text>
        </div>

        <div className="user-info" style={{ padding: '8px', borderBottom: '1px solid #eee' }}>
          <span>Current user: {userInfo.email}</span>
        </div>

        <Group>
          <Button
            variant="light"
            leftIcon={<IconMessageCircle size={16} />}
            onClick={() => setShowChat(!showChat)}
          >
            {showChat ? 'Hide Chat' : 'Show Chat'}
          </Button>
          <Menu>
            <Menu.Target>
              <Button
                leftIcon={<IconPlus size={16} />}
                variant="gradient"
                gradient={{ from: 'blue', to: 'cyan' }}
              >
                New Segment
              </Button>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item onClick={() => {
                setActiveSegmentType('conditions');
                setSegmentName('');
                setConditions({});
                setStats(null);
                setShowSqlEditor(false);
              }}>
                Using Conditions
              </Menu.Item>
              <Menu.Item onClick={() => {
                setActiveSegmentType('sql');
                setShowSqlEditor(true);
                setSqlQuery('');
                setSqlSegmentName('');
                setSqlStats(null);
                setConditions({});
              }}>
                Using SQL Query
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>
      </Group>

      <Box className="fade-in" py="xl">
        <Collapse in={showChat} mb="xl">
          <ChatWindow />
        </Collapse>

        <Paper shadow="sm" radius="md" p="md" withBorder mb="xl">
          <Group position="apart">
            <Title order={3}>Input Table Metadata</Title>
            <Button
              variant="subtle"
              onClick={() => setShowMetadata(!showMetadata)}
              rightIcon={showMetadata ? '↑' : '↓'}
            >
              {showMetadata ? 'Hide' : 'Show'} Metadata
            </Button>
          </Group>

          <Collapse in={showMetadata}>
            <Box mt="md">
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Column Name</Table.Th>
                    <Table.Th>Data Type</Table.Th>
                    <Table.Th>Business Description</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {columns.map((col) => (
                    <Table.Tr key={col.name}>
                      <Table.Td><code>{col.name}</code></Table.Td>
                      <Table.Td>{col.type}</Table.Td>
                      <Table.Td>{col.description}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Box>
          </Collapse>
        </Paper>

        {activeSegmentType === 'conditions' && (
          <Paper shadow="sm" radius="md" p="md" withBorder className="segment-container">
            <Group mb="lg" position="apart">
              <Title order={3}>Segment Conditions</Title>
              <MultiSelect
                icon={<IconFilter size={16} />}
                label="Add condition"
                placeholder="Select column"
                data={columns.map(col => ({ value: col.name, label: col.name }))}
                value={[]}
                onChange={(value) => {
                  if (value.length > 0) {
                    addCondition(value[value.length - 1]);
                  }
                }}
                searchable
                clearable
              />
            </Group>

            <Stack spacing="md">
              {Object.entries(conditions).map(([column, condition]) => {
                const columnData = columns.find(c => c.name === column);
                return (
                  <Transition key={column} transition="fade" mounted={true}>
                    {(styles) => (
                      <Card key={column} withBorder style={styles} className="card">
                        <Group position="apart" mb="sm">
                          <Group spacing="xs">
                            <Title order={4}>{column}</Title>
                            <Badge size="sm">{columnData?.type}</Badge>
                          </Group>
                          <ActionIcon
                            color="red"
                            variant="light"
                            onClick={() => deleteCondition(column)}
                          >
                            <IconTrash size={16} />
                          </ActionIcon>
                        </Group>
                        {columnData?.type === 'Integer' || columnData?.type === 'Float' ? (
                          <Group spacing="md">
                            <NumberInput
                              label="Min"
                              value={condition.min || ''}
                              onChange={(value) => updateCondition(column, 'min', value)}
                              styles={{ input: { width: '100%' } }}
                            />
                            <NumberInput
                              label="Max"
                              value={condition.max || ''}
                              onChange={(value) => updateCondition(column, 'max', value)}
                              styles={{ input: { width: '100%' } }}
                            />
                          </Group>
                        ) : (
                          <MultiSelect
                            label="Values"
                            data={columnData?.unique_values?.map(v => ({ value: v, label: v })) || []}
                            value={condition.values}
                            onChange={(value) => updateCondition(column, 'values', value)}
                            searchable
                            clearable
                          />
                        )}
                      </Card>
                    )}
                  </Transition>
                );
              })}
            </Stack>

            {stats && (
              <Paper p="md" mt="xl" radius="md" withBorder>
                <Group position="apart">
                  <Text weight={500}>Matching Customers</Text>
                  <Badge size="lg" variant="gradient" gradient={{ from: 'blue', to: 'cyan' }}>
                    {stats.count} / {stats.total} ({stats.percentage}%)
                  </Badge>
                </Group>
              </Paper>
            )}

            <Divider my="xl" />

            <Group position="right">
              <TextInput
                placeholder="Enter segment name"
                value={segmentName}
                onChange={(e) => setSegmentName(e.currentTarget.value)}
                style={{ flex: 1 }}
              />
              <Button
                onClick={handleSaveSegment}
                disabled={!segmentName}
                variant="filled"
              >
                Save Segment
              </Button>
            </Group>
          </Paper>
        )}

        {showSqlEditor && (
          <Paper shadow="sm" radius="md" p="md" withBorder className="segment-container">
            <Title order={2} mb="lg">Create SQL Segment</Title>

            <Textarea
              label="SQL Query"
              placeholder="Enter your SQL query"
              minRows={4}
              value={sqlQuery}
              onChange={(e) => setSqlQuery(e.currentTarget.value)}
              mb="md"
            />

            {sqlStats && (
              <Alert icon={<IconInfoCircle size={16} />} color="blue" mb="md">
                Query matches {sqlStats.count} customers ({sqlStats.percentage}% of total)
              </Alert>
            )}

            <Group position="apart" mt="xl">
              <Button
                variant="light"
                onClick={() => {
                  setShowSqlEditor(false);
                  setSqlQuery('');
                  setSqlSegmentName('');
                  setSqlStats(null);
                }}
              >
                Cancel
              </Button>
              <Group>
                <Button
                  variant="light"
                  onClick={evaluateSqlSegment}
                  disabled={!sqlQuery}
                >
                  Test Query
                </Button>
                <TextInput
                  placeholder="Enter segment name"
                  value={sqlSegmentName}
                  onChange={(e) => setSqlSegmentName(e.currentTarget.value)}
                  style={{ width: '200px' }}
                />
                <Button
                  onClick={handleSaveSqlSegment}
                  disabled={!sqlSegmentName || !sqlQuery}
                  variant="filled"
                >
                  Save SQL Segment
                </Button>
              </Group>
            </Group>
          </Paper>
        )}

        {segments.length > 0 && (
          <Paper shadow="sm" radius="md" p="md" withBorder mt="xl" className="segment-container">
            <Title order={2} mb="lg">Saved Segments</Title>
            <Stack spacing="md">
              {segments.map((segment) => (
                <Card key={segment.name} withBorder className="card">
                  <Group position="apart">
                    <Stack spacing="xs">
                      <Title order={3}>{segment.name}</Title>
                      <Group spacing="xs">
                        <Text color="dimmed" size="sm">
                          {segment.type === 'sql' ? 'SQL Query' : `${Object.keys(segment.conditions).length} conditions`}
                        </Text>
                        <Text color="dimmed" size="xs">•</Text>
                        <Text color="dimmed" size="sm">
                          Created by {segment.creator?.email || 'Unknown'}
                        </Text>
                      </Group>
                    </Stack>
                    <Group spacing="xs">
                      <Button
                        variant="light"
                        leftIcon={<IconDownload size={16} />}
                        onClick={() => handleExportNow(segment.name)}
                      >
                        Export
                      </Button>
                      <Button
                        variant="light"
                        leftIcon={<IconClock size={16} />}
                        onClick={() => {
                          setSelectedSegment(segment.name);
                          setScheduleModalOpen(true);
                        }}
                      >
                        Schedule
                      </Button>
                      <Button
                        variant="light"
                        color="red"
                        leftIcon={<IconTrash size={16} />}
                        onClick={() => deleteSegment(segment.name)}
                      >
                        Delete
                      </Button>
                    </Group>
                  </Group>
                </Card>
              ))}
            </Stack>
          </Paper>
        )}

        {schedules.length > 0 && (
          <Paper shadow="sm" radius="md" p="md" withBorder mt="xl" className="segment-container">
            <Title order={2} mb="lg">Scheduled Exports</Title>
            <Table highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Segment</Table.Th>
                  <Table.Th>Format</Table.Th>
                  <Table.Th>Destination</Table.Th>
                  <Table.Th>Schedule</Table.Th>
                  <Table.Th>Last Run</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {schedules.map((schedule, index) => (
                  <Table.Tr key={index}>
                    <Table.Td>{schedule.segment_name}</Table.Td>
                    <Table.Td>
                      <Badge>{schedule.format.toUpperCase()}</Badge>
                    </Table.Td>
                    <Table.Td>
                      <Badge>{schedule.destination}</Badge>
                    </Table.Td>
                    <Table.Td>
                      {schedule.run_time ?
                        `Daily at ${schedule.run_time}` :
                        `Every ${schedule.interval_hours} hours`}
                    </Table.Td>
                    <Table.Td>{schedule.last_run || 'Never'}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Paper>
        )}
      </Box>

      <Modal
        opened={scheduleModalOpen}
        onClose={() => setScheduleModalOpen(false)}
        title="Schedule Segment Export"
        size="md"
        radius="md"
        centered
        padding="xl"
        styles={{
          inner: { padding: '20px' },
          content: {
            maxWidth: '450px',
            width: '100%',
            margin: 'auto'
          }
        }}
      >
        <Stack spacing="md">
          <Select
            label="Export Format"
            value={exportFormat}
            onChange={setExportFormat}
            data={[
              { value: 'csv', label: 'CSV' },
              { value: 'json', label: 'JSON' },
              { value: 'parquet', label: 'Parquet' }
            ]}
          />

          <Select
            label="Export Destination"
            value={exportDestination}
            onChange={setExportDestination}
            data={[
              { value: 'none', label: 'No destination (local export)' },
              { value: 'salesforce', label: 'Salesforce' },
              { value: 'facebook', label: 'Facebook' },
              { value: 'google_ads', label: 'Google Ads' }
            ]}
          />

          <SegmentedControl
            fullWidth
            value={scheduleType}
            onChange={setScheduleType}
            data={[
              { label: 'Every X Hours', value: 'interval' },
              { label: 'Daily at Time', value: 'time' }
            ]}
          />

          {scheduleType === 'interval' ? (
            <NumberInput
              label="Export Interval (hours)"
              value={scheduleInterval}
              onChange={(val) => setScheduleInterval(val)}
              min={1}
            />
          ) : (
            <TimeInput
              label="Export Time (24h)"
              value={scheduleTime}
              onChange={(event) => setScheduleTime(event.currentTarget.value)}
            />
          )}

          <Button
            onClick={handleScheduleExport}
            fullWidth
            variant="gradient"
            gradient={{ from: 'blue', to: 'cyan' }}
          >
            Schedule Export
          </Button>
        </Stack>
      </Modal>
    </Container>
  );
}

export default App;
