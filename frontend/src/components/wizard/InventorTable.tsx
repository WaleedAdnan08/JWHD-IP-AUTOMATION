import React from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Trash2, Plus } from 'lucide-react';

export interface Inventor {
  first_name: string;
  middle_name?: string;
  last_name: string;
  suffix?: string;
  street_address?: string;
  city?: string;
  state?: string;
  zip_code?: string;
  country?: string;
  citizenship?: string;
}

interface InventorTableProps {
  inventors: Inventor[];
  setInventors: (inventors: Inventor[]) => void;
}

export const InventorTable: React.FC<InventorTableProps> = ({ inventors, setInventors }) => {
  
  const handleInputChange = (index: number, field: keyof Inventor, value: string) => {
    const newInventors = [...inventors];
    newInventors[index] = { ...newInventors[index], [field]: value };
    setInventors(newInventors);
  };

  const removeInventor = (index: number) => {
    const newInventors = inventors.filter((_, i) => i !== index);
    setInventors(newInventors);
  };

  const addInventor = () => {
    setInventors([...inventors, { first_name: '', last_name: '', citizenship: '' }]);
  };

  return (
    <div className="w-full space-y-4">
      <div className="rounded-md border">
        <div className="w-full overflow-auto">
          <table className="w-full caption-bottom text-sm">
            <thead className="[&_tr]:border-b">
              <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground w-[25%]">Name</th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground w-[35%]">Address</th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground w-[15%]">Citizenship</th>
                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground w-[50px]"></th>
              </tr>
            </thead>
            <tbody className="[&_tr:last-child]:border-0">
              {inventors.map((inventor, index) => (
                <tr key={index} className="border-b transition-colors hover:bg-muted/50">
                  <td className="p-4 align-middle">
                    <div className="space-y-2">
                        <div className="flex gap-1">
                            <Input
                            value={inventor.first_name || ''}
                            onChange={(e) => handleInputChange(index, 'first_name', e.target.value)}
                            placeholder="First"
                            className="flex-1"
                            />
                            <Input
                            value={inventor.middle_name || ''}
                            onChange={(e) => handleInputChange(index, 'middle_name', e.target.value)}
                            placeholder="Middle"
                            className="w-16"
                            />
                        </div>
                        <div className="flex gap-1">
                            <Input
                            value={inventor.last_name || ''}
                            onChange={(e) => handleInputChange(index, 'last_name', e.target.value)}
                            placeholder="Last / Family"
                            className="flex-1"
                            />
                             <Input
                            value={inventor.suffix || ''}
                            onChange={(e) => handleInputChange(index, 'suffix', e.target.value)}
                            placeholder="Sfx"
                            className="w-14"
                            />
                        </div>
                    </div>
                  </td>
                  <td className="p-4 align-middle">
                    <div className="space-y-2">
                       <Input 
                        value={inventor.street_address || ''} 
                        onChange={(e) => handleInputChange(index, 'street_address', e.target.value)}
                        placeholder="Street Address"
                        className="mb-1"
                      />
                      <div className="flex gap-1">
                         <Input 
                          value={inventor.city || ''} 
                          onChange={(e) => handleInputChange(index, 'city', e.target.value)}
                          placeholder="City"
                        />
                         <Input 
                          value={inventor.state || ''} 
                          onChange={(e) => handleInputChange(index, 'state', e.target.value)}
                          placeholder="State"
                          className="w-20"
                        />
                      </div>
                    </div>
                  </td>
                  <td className="p-4 align-middle">
                    <Input 
                      value={inventor.citizenship || ''} 
                      onChange={(e) => handleInputChange(index, 'citizenship', e.target.value)}
                      placeholder="Country Code (e.g. US)"
                    />
                  </td>
                  <td className="p-4 align-middle">
                    <Button 
                      variant="ghost" 
                      size="icon"
                      onClick={() => removeInventor(index)}
                      className="text-red-500 hover:text-red-700 hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <Button onClick={addInventor} variant="outline" className="w-full border-dashed">
        <Plus className="mr-2 h-4 w-4" /> Add Inventor
      </Button>
    </div>
  );
};