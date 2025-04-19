import { useState, useEffect } from 'react';
import axios from 'axios';
import { Box, Button, Group, MultiSelect, NumberInput, TextInput, Title, Text, Stack, Card, ActionIcon } from '@mantine/core';
import { IconTrash } from '@tabler/icons-react';

function App() {
  const [columns, setColumns] = useState([]);
  const [segments, setSegments] = useState([]);
  const [conditions, setConditions] = useState({});
  const [segmentName, setSegmentName] = useState('');
  const [stats, setStats] = useState(null);

  useEffect(() => {
    loadColumns();
    loadSegments();
  }, []);

  useEffect(() => {
    if (Object.keys(conditions).length > 0) {
      evaluateSegment();
    } else {
      setStats(null);
    }
  }, [conditions]);

  const loadColumns = async () => {
    const response = await axios.get('http://localhost:8000/api/columns');
    setColumns(response.data.columns);
  };

  const loadSegments = async () => {
    const response = await axios.get('http://localhost:8000/api/segments');
    setSegments(response.data);
  };

  const evaluateSegment = async () => {
    const response = await axios.post('http://localhost:8000/api/evaluate-segment', conditions);
    setStats(response.data);
  };

  const handleSaveSegment = async () => {
    if (!segmentName) return;
    await axios.post('http://localhost:8000/api/save-segment', {
      name: segmentName,
      conditions
    });
    loadSegments();
    setSegmentName('');
  };

  const addCondition = (column) => {
    const columnData = columns.find(c => c.name === column);
    if (columnData.type.includes('int') || columnData.type.includes('float')) {
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

  return (
    <Box p="xl">
      <Title order={1} mb="lg">Customer Segmentation</Title>
      
      <Group mb="xl">
        <MultiSelect
          label="Add condition"
          placeholder="Select column"
          data={columns.map(col => ({ value: col.name, label: col.name }))}
          value={[]}
          onChange={(value) => {
            if (value.length > 0) {
              addCondition(value[value.length - 1]);
            }
          }}
        />
      </Group>

      <Stack spacing="md" mb="xl">
        {Object.entries(conditions).map(([column, condition]) => {
          const columnData = columns.find(c => c.name === column);
          return (
            <Card key={column} withBorder>
              <Group position="apart" mb="sm">
                <Title order={4}>{column}</Title>
                <ActionIcon color="red" onClick={() => deleteCondition(column)}>
                  <IconTrash size={16} />
                </ActionIcon>
              </Group>
              {columnData?.type.includes('int') || columnData?.type.includes('float') ? (
                <Group>
                  <NumberInput
                    label="Min"
                    value={condition.min || ''}
                    onChange={(value) => updateCondition(column, 'min', value)}
                  />
                  <NumberInput
                    label="Max"
                    value={condition.max || ''}
                    onChange={(value) => updateCondition(column, 'max', value)}
                  />
                </Group>
              ) : (
                <MultiSelect
                  label="Values"
                  data={columnData?.unique_values?.map(v => ({ value: v, label: v })) || []}
                  value={condition.values}
                  onChange={(value) => updateCondition(column, 'values', value)}
                />
              )}
            </Card>
          );
        })}
      </Stack>

      {stats && (
        <Card withBorder mb="xl">
          <Text>Matching customers: {stats.count} out of {stats.total} ({stats.percentage}%)</Text>
        </Card>
      )}

      <Group>
        <TextInput
          placeholder="Segment name"
          value={segmentName}
          onChange={(e) => setSegmentName(e.currentTarget.value)}
        />
        <Button onClick={handleSaveSegment}>Save Segment</Button>
      </Group>

      {segments.length > 0 && (
        <>
          <Title order={2} mt="xl" mb="md">Saved Segments</Title>
          <Stack>
            {segments.map((segment) => (
              <Card key={segment.name} withBorder>
                <Title order={3}>{segment.name}</Title>
                <Text>{Object.keys(segment.conditions).length} conditions</Text>
              </Card>
            ))}
          </Stack>
        </>
      )}
    </Box>
  );
}

export default App;
